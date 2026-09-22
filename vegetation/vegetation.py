from ..core.node import Thing,Dimension
from ..core.domain import VolumeDomain,Bounds
from ..core.constraints import Commitment
from ..core.seed import RandomStream,stable_id,derive_seed
from ..core.scope import Transform
from ..refinement.refiner import Refiner,RefinementResult
from ..refinement.budget import Cost
from ..representation.provider import RepresentationProvider
from ..representation.geometry import GeometryBundle,Instance,box_instance,Mesh
from .morpho_adapter import PlantRequest


class VegetationRefiner(Refiner):
    key='vegetation.individual_trees'; supported_types=('Forest','Park'); capability='individual trees'
    def estimate_cost(self,node,context):
        n=node.semantic_state['tree_count']; return Cost(nodes=n,memory_bytes=n*1500)
    def refine(self,node,context):
        b=node.domain.bounds; x,y=b.minimum[:2]; w,h=b.size[:2]; rng=RandomStream(node.seed,'trees')
        count=node.semantic_state['tree_count']; children=[]
        for i in range(count):
            radius=min(4.,w/10,h/10)
            px=x+radius+rng.unit('x',i)*(w-2*radius); py=y+radius+rng.unit('y',i)*(h-2*radius)
            z=context.environment.height(px,py)
            if z<=context.environment.sea_level+.3: continue
            height=node.semantic_state['maximum_height']*rng.uniform(.65,1.,'height',i)
            d=VolumeDomain(Bounds((px-radius,py-radius,z),(px+radius,py+radius,z+height)))
            state={'species':node.semantic_state['species'],'maximum_height':height,'maximum_radius':radius,
                   'position':[px,py,z],'maturity_age':30.}
            children.append(Thing(stable_id(node.id,'Tree',i),'Tree',derive_seed(node.seed,'tree',i),d,state,
                                  (node.id,),created_at=node.created_at,commitments=tuple(Commitment(k,v) for k,v in state.items())))
        return RefinementResult(Dimension.STRUCTURAL,1,{'materialized_tree_count':len(children)},tuple(children))


class VegetationAreaProvider(RepresentationProvider):
    key='vegetation.area_proxy'; supported_types=('Forest','Park'); max_level=0; time_dependent=True
    def realize(self,node,detail_request,context):
        b=node.domain.bounds; x,y=b.center[:2]; w,h=b.size[:2]
        z=context.environment.height(x,y); instances=[]; meshes=[]
        if node.type_id=='Park':
            verts=tuple((p[0],p[1],context.environment.height(*p[:2])+.07) for p in node.domain.vertices)
            meshes.append(Mesh(verts,((0,1,2,3),),'park','park'))
        if not node.child_ids:
            age=max(0,context.time-node.created_at); growth=min(1.,max(.12,age/40))
            for sx,sy in ((-.2,-.2),(-.2,.2),(.2,-.2),(.2,.2)):
                px,py=x+sx*w,y+sy*h; base=context.environment.height(px,py)
                height=node.semantic_state['maximum_height']*growth
                instances.append(Instance('canopy',Transform((px,py,base+height*.6),(w*.43,h*.43,height)),'foliage'))
        return GeometryBundle(tuple(meshes),tuple(instances))


class TreeProvider(RepresentationProvider):
    key='vegetation.tree'; supported_types=('Tree',); max_level=2; time_dependent=True
    def realize(self,node,detail_request,context):
        s=node.semantic_state; x,y,z=s['position']; age=max(0,context.time-node.created_at)
        growth=min(1.,max(.08,age/s['maturity_age'])); height=s['maximum_height']*growth
        radius=s['maximum_radius']*growth
        if detail_request>=2 and context.vegetation_adapter is not None:
            req=PlantRequest(node.id,node.seed,s['species'],age,(x,y,z),height,radius,
                             context.environment.sample(x,y),detail_request)
            result=context.vegetation_adapter.realize(req)
            # External meshes and instance geometry must fit the committed envelope.
            from ..representation.geometry import PROTOTYPES
            prototypes={**PROTOTYPES,**dict(result.prototypes)}
            meshes=list(result.meshes)+[prototypes[i.prototype].transformed(i.transform) for i in result.instances]
            if any(not node.domain.contains_point(p) for m in meshes for p in m.vertices):
                raise ValueError('Plant adapter escaped its committed tree domain')
            return result
        trunk=max(.12,radius*.16)
        instances=[box_instance((x,y,z+height*.3),(trunk,trunk,height*.6),'bark'),
                   Instance('canopy',Transform((x,y,z+height*.66),(radius*2,radius*2,height*.65)),'foliage')]
        if detail_request>=1:
            for sx,sy in ((-.36,0),(.36,0),(0,.36)):
                instances.append(Instance('canopy',Transform((x+sx*radius,y+sy*radius,z+height*.72),
                                                             (radius*1.05,radius*1.05,height*.44)),'foliage'))
        return GeometryBundle(instances=tuple(instances))
