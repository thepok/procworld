"""Budget-limited, backend-neutral semantic diagnostic overlays."""
from ..core.domain import UnboundedDomain
from ..representation.geometry import GeometryScene,GeometryBundle,Mesh,ribbon,MATERIALS
from ..core.seed import derive_seed


def debug_scene(snapshot,mode='DOMAINS',maximum_nodes=2000):
    scene=GeometryScene()
    if mode=='NONE': return scene
    used=snapshot.scene.cost(); limits=snapshot.report['budget']['limits']
    triangles=max(0,limits['max_triangles']-used.triangles)
    instances=max(0,limits['max_instances']-used.instances)
    for node in snapshot.graph.active(snapshot.time):
        if len(scene.bundles)>=maximum_nodes: break
        if node.category!='thing' or isinstance(node.domain,UnboundedDomain): continue
        if node.type_id not in {'Building','Road','Block','Parcel','Park','Tree'}: continue
        b=node.domain.bounds; x,y,z=b.minimum; X,Y,Z=b.maximum
        material='debug'; meshes=[]
        if mode=='DOMAINS':
            altitude=Z+.3 if node.type_id in {'Building','Tree'} else snapshot.graph[node.id].anchor[2]+.3
            if altitude<1: altitude=max(p[2] for p in getattr(node.domain,'points',((0,0,0),)))+.3
            # Area domains describe footprints; align their debug lines to nearby terrain.
            if node.type_id in {'Block','Parcel','Park'}:
                parent_id=next(iter(node.child_ids),None)
                if parent_id: altitude=max(altitude,snapshot.graph[parent_id].anchor[2]+.3)
            points=((x,y,altitude),(X,y,altitude),(X,Y,altitude),(x,Y,altitude),(x,y,altitude))
            meshes.append(ribbon(points,.7,'debug','domain_outline'))
        else:
            if mode=='AGE':
                value=min(1,max(0,snapshot.time-node.created_at)/180)
            elif mode=='PRESSURE':
                value=min(1,max(0,node.semantic_state.get('development_pressure',.5)))
            else:
                value=(derive_seed(0,node.type_id)%100)/99
            bucket=int(value*9); material=f'debug_heat_{bucket}'
            MATERIALS[material]=(.15+.8*value,.65*(1-value)+.1,.8*(1-value)+.1,1.)
            altitude=Z+.35
            meshes.append(Mesh(((x,y,altitude),(X,y,altitude),(X,Y,altitude),(x,Y,altitude)),((0,1,2,3),),material,'semantic_overlay'))
        bundle=GeometryBundle(meshes=tuple(meshes)); cost=bundle.cost()
        if cost.triangles>triangles or cost.instances>instances: continue
        key='Debug:'+node.id; scene.bundles[key]=bundle; scene.categories[key]='Debug'
        triangles-=cost.triangles; instances-=cost.instances
    return scene
