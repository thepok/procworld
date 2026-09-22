"""Acyclic graph, semantic-event mutation, atomic additive refinement."""
from __future__ import annotations
import copy
from .node import ProceduralNode, Dimension, node_from_data
from .constraints import CommitmentViolation, Commitment
from .domain import UnboundedDomain
from .seed import canonical, digest


class SemanticGraph:
    def __init__(self):
        self.nodes: dict[str,ProceduralNode]={}
    def __len__(self):
        return len(self.nodes)
    def __getitem__(self,node_id):
        return self.nodes[node_id]
    def add(self,node:ProceduralNode,check_domain:bool=True):
        if node.id in self.nodes:
            old=self.nodes[node.id]
            # Child links are maintained by the graph and not part of creation identity.
            a=old.to_data(); b=node.to_data(); a['child_ids']=b['child_ids']=()
            if canonical(a)!=canonical(b):
                raise CommitmentViolation(f'Identity collision: {node.id}')
            return
        for pid in node.parent_ids:
            if pid not in self.nodes:
                raise CommitmentViolation(f'Missing parent {pid}')
            parent=self.nodes[pid]
            if check_domain and not parent.domain.contains_domain(node.domain):
                raise CommitmentViolation(f'{node.id} escapes parent domain {pid}')
            if node.created_at < parent.created_at:
                raise CommitmentViolation('Child predates its parent')
            if parent.destroyed_at is not None:
                if node.created_at >= parent.destroyed_at:
                    raise CommitmentViolation('Child is born after parent destruction')
                node.destroyed_at=min(node.destroyed_at or parent.destroyed_at,parent.destroyed_at)
        node.validate()
        self.nodes[node.id]=node.copy()
        for pid in node.parent_ids:
            p=self.nodes[pid]
            p.child_ids=tuple(sorted(set(p.child_ids+(node.id,))))
    def update(self,node_id:str,facts:dict):
        node=self.nodes[node_id].copy()
        node.semantic_state.update(copy.deepcopy(facts)); node.validate(); node.version+=1
        self.nodes[node_id]=node
    def destroy(self,node_id:str,time:float):
        node=self.nodes[node_id]
        if time < node.created_at:
            raise CommitmentViolation('Destruction before construction')
        if node.destroyed_at is not None and node.destroyed_at != time:
            raise CommitmentViolation('Conflicting destruction dates')
        node.destroyed_at=time; node.version+=1
        for child in node.child_ids:
            c=self.nodes[child]
            if c.destroyed_at is None or c.destroyed_at > time:
                self.destroy(child,time)
    def is_active(self,node_id:str,time:float,_memo:dict|None=None) -> bool:
        memo={} if _memo is None else _memo
        if node_id not in memo:
            n=self.nodes[node_id]
            memo[node_id]=n.exists_at(time) and all(self.is_active(p,time,memo) for p in n.parent_ids)
        return memo[node_id]
    def active(self,time:float):
        memo={}
        return [self.nodes[k] for k in sorted(self.nodes) if self.is_active(k,time,memo)]
    def refine(self,parent_id:str,dimension:Dimension,level:int,
               facts:dict|None=None,children:tuple[ProceduralNode,...]=()):
        """Validate a small transaction before touching authoritative records."""
        original=self.nodes[parent_id]
        parent=original.copy()
        for key,value in (facts or {}).items():
            if key in parent.semantic_state and canonical(parent.semantic_state[key]) != canonical(value):
                raise CommitmentViolation(f'Refinement attempts to overwrite {key}')
            parent.semantic_state[key]=copy.deepcopy(value)
        parent.refinement_state.advance(dimension,level)
        parent.validate(); parent.version+=1
        staged={parent_id:parent}
        if len({c.id for c in children}) != len(children):
            raise CommitmentViolation('Duplicate child identities')
        for child in children:
            if child.id in self.nodes or child.id in staged:
                raise CommitmentViolation(f'Refinement child already exists: {child.id}')
            if parent_id not in child.parent_ids:
                raise CommitmentViolation('Refinement child must be owned by its source parent')
            child=child.copy()
            for pid in child.parent_ids:
                p=staged.get(pid,self.nodes.get(pid))
                if p is None:
                    raise CommitmentViolation('Unresolved refinement parent')
                if not p.domain.contains_domain(child.domain):
                    raise CommitmentViolation(f'{child.id} escapes {pid}')
                if child.created_at < p.created_at:
                    raise CommitmentViolation('Child predates parent')
                if p.destroyed_at is not None:
                    if child.created_at >= p.destroyed_at:
                        raise CommitmentViolation('Child is born outside parent lifetime')
                    child.destroyed_at=min(child.destroyed_at or p.destroyed_at,p.destroyed_at)
            child.validate(); staged[child.id]=child
        # All checks passed. Only now publish the additions.
        for cid,child in list(staged.items()):
            if cid == parent_id:
                continue
            for pid in child.parent_ids:
                if pid not in staged:
                    staged[pid]=self.nodes[pid].copy()
                p=staged[pid]; p.child_ids=tuple(sorted(set(p.child_ids+(cid,))))
        self.nodes.update(staged)
    def specialize(self,node_id:str,type_id:str,registry):
        node=self.nodes[node_id]
        if not registry.is_a(type_id,node.type_id):
            raise CommitmentViolation('Specialization must be a semantic subtype')
        node.type_id=type_id; node.version+=1
    def copy(self):
        result=SemanticGraph(); result.nodes=copy.deepcopy(self.nodes); return result
    def to_data(self):
        return [self.nodes[k].to_data() for k in sorted(self.nodes)]
    def fingerprint(self):
        return digest(self.to_data())
    @classmethod
    def from_data(cls,data):
        graph=cls(); pending={d['id']:node_from_data(d) for d in data}
        if len(pending)!=len(data):
            raise ValueError('Duplicate node IDs in serialized graph')
        expected={k:tuple(sorted(n.child_ids)) for k,n in pending.items()}
        for n in pending.values(): n.child_ids=()
        while pending:
            ready=sorted(k for k,n in pending.items() if all(p in graph.nodes for p in n.parent_ids))
            if not ready:
                raise ValueError('Cycle or missing graph parent')
            for k in ready: graph.add(pending.pop(k))
        if any(tuple(sorted(graph[k].child_ids)) != c for k,c in expected.items()):
            raise ValueError('Inconsistent serialized child links')
        return graph
