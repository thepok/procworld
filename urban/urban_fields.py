"""First aggregate development policy. Replaceable without a geometry dependency."""
import math


class DevelopmentPolicy:
    version='1.0.0'
    def score(self,environment,x,y,center,year,level,influences):
        distance=math.hypot(x-center[0],y-center[1])
        accessibility=1/(1+distance/300)
        suitability=environment.settlement_suitability(x,y)
        pressure=.5*accessibility+.5*suitability
        if level>=1: pressure-=environment.slope(x,y)*.8
        if level>=2:
            pressure+=.15*environment.fertility(x,y)
            pressure-=max(0,environment.height(x,y)-environment.sea_level-80)/300
        for field in influences:
            if field.kind in {'GrowthAttractor','CommercialCenter','TransportHub','IndustrialAttractor'}:
                pressure+=field.sample((x,y,environment.height(x,y)),year)
            elif field.kind=='GrowthRepulsor':
                pressure-=field.sample((x,y,environment.height(x,y)),year)
        return {'accessibility':accessibility,'development_pressure':max(0,pressure),
                'land_value':max(0,pressure)*100,'suitability':suitability}
