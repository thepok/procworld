"""Absolute-coordinate environmental fields; requested scene extents are never inputs."""
from __future__ import annotations
from functools import lru_cache
import math
from ..core.seed import derive_seed,RandomStream


def _smooth(t): return t*t*t*(t*(t*6-15)+10)


class WorldFields:
    version='1.0.0'
    def __init__(self,seed:int,sea_level:float=0.):
        self.seed=seed; self.sea_level=sea_level
        self.seeds={name:derive_seed(seed,'field',name) for name in
                    ('continental','hills','detail','rock','moisture','temperature','geology')}
    @staticmethod
    @lru_cache(maxsize=131072)
    def _lattice(seed,x,y):
        return ((derive_seed(seed,x,y)>>11)/(1<<53))*2-1
    def noise(self,name,x,y):
        ix,iy=math.floor(x),math.floor(y); u,v=_smooth(x-ix),_smooth(y-iy)
        seed=self.seeds[name]
        a=self._lattice(seed,ix,iy); b=self._lattice(seed,ix+1,iy)
        c=self._lattice(seed,ix,iy+1); d=self._lattice(seed,ix+1,iy+1)
        return (a+(b-a)*u)*(1-v)+(c+(d-c)*u)*v
    @lru_cache(maxsize=131072)
    def height(self,x:float,y:float) -> float:
        return (self.sea_level+32+105*self.noise('continental',x/9000,y/9000)
                +38*self.noise('hills',x/1900,y/1900)
                +11*self.noise('detail',x/380,y/380)+2.4*self.noise('rock',x/85,y/85))
    elevation=height
    def moisture(self,x,y): return .5+.5*self.noise('moisture',x/2700,y/2700)
    def temperature(self,x,y):
        return 17+11*self.noise('temperature',x/15000,y/15000)-max(0,self.height(x,y)-self.sea_level)*.0065
    def geology(self,x,y):
        return int((self.noise('geology',x/4200,y/4200)+1)*1.4999)
    def normal(self,x,y):
        dx=(self.height(x+8,y)-self.height(x-8,y))/16
        dy=(self.height(x,y+8)-self.height(x,y-8))/16
        length=math.sqrt(dx*dx+dy*dy+1)
        return (-dx/length,-dy/length,1/length)
    def slope(self,x,y):
        n=self.normal(x,y); return math.sqrt(n[0]*n[0]+n[1]*n[1])/n[2]
    def water_table(self,x,y): return min(self.height(x,y)-2,self.sea_level+5*self.moisture(x,y))
    def biome(self,x,y):
        h=self.height(x,y)
        if h<self.sea_level: return 'ocean'
        if h<self.sea_level+3: return 'coast'
        if h>120: return 'upland'
        if self.temperature(x,y)<3: return 'cold_grassland'
        return 'forest' if self.moisture(x,y)>.48 else 'grassland'
    def fertility(self,x,y):
        return self.moisture(x,y)*max(0,1-self.slope(x,y)*2)
    def settlement_suitability(self,x,y):
        h=self.height(x,y)
        if h<=self.sea_level+2: return 0.
        return math.exp(-abs(h-self.sea_level-28)/180)*max(0,1-self.slope(x,y)*3)*(.5+.5*self.moisture(x,y))
    def sample(self,x,y):
        return {'elevation':self.height(x,y),'normal':self.normal(x,y),'slope':self.slope(x,y),
                'moisture':self.moisture(x,y),'temperature':self.temperature(x,y),
                'water_table':self.water_table(x,y),'geology':self.geology(x,y),
                'biome':self.biome(x,y),'fertility':self.fertility(x,y),
                'settlement_suitability':self.settlement_suitability(x,y)}
