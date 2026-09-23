// GFS bilinear sampling; particle speeds are visually accelerated, not real-time trajectories.
export function sampleWind(grid,lat,lon) {
    const x=(lon-grid.west)/grid.dx, y=(grid.north-lat)/grid.dy;
    const i=Math.floor(x),j=Math.floor(y);
    if(i<0 || j<0 || i>=grid.width-1 || j>=grid.height-1)return null;
    const indices=[j*grid.width+i,j*grid.width+i+1,(j+1)*grid.width+i,(j+1)*grid.width+i+1];
    const interpolate=values => {
        const v=indices.map(n => values[n]);
        if(v.some(n => !Number.isFinite(n)))return null;
        const a=x-i,b=y-j;
        return v[0]*(1-a)*(1-b)+v[1]*a*(1-b)+v[2]*(1-a)*b+v[3]*a*b;
    };
    const u=interpolate(grid.u),v=interpolate(grid.v);
    return u==null || v==null ? null : [u,v];
}
export class WindParticles {
    constructor(map,grid) {
        this.map=map;this.grid=grid;this.stopped=false;
        this.canvas=document.createElement('canvas');this.canvas.className='wind-canvas';map.getContainer().append(this.canvas);
        this.ctx=this.canvas.getContext('2d');this.reset=this.reset.bind(this);
        map.on('moveend resize',this.reset);this.reset();this.tick=this.tick.bind(this);this.frame=requestAnimationFrame(this.tick);
    }
    particle() {
        const size=this.map.getSize();const coord=this.map.containerPointToLatLng([Math.random()*size.x,Math.random()*size.y]);
        return {lat:coord.lat,lon:coord.lng,age:Math.random()*80};
    }
    reset() {
        const size=this.map.getSize();this.canvas.width=size.x;this.canvas.height=size.y;
        this.particles=Array.from({length:window.matchMedia('(max-width:700px)').matches?350:1100},()=>this.particle());
    }
    tick(now) {
        if(this.stopped)return;
        const dt=Math.min((now-(this.last || now))/1000,.05);this.last=now;
        const ctx=this.ctx;
        ctx.globalCompositeOperation='destination-in';ctx.fillStyle='rgba(0,0,0,.92)';ctx.fillRect(0,0,this.canvas.width,this.canvas.height);
        ctx.globalCompositeOperation='source-over';ctx.lineWidth=1.1;
        for(let i=0;i<this.particles.length;i++) {
            let p=this.particles[i];const vector=sampleWind(this.grid,p.lat,p.lon);
            if(!vector || p.age>100){this.particles[i]=this.particle();continue;}
            const a=this.map.latLngToContainerPoint([p.lat,p.lon]);
            p.lat+=vector[1]*dt*1600/111320;p.lon+=vector[0]*dt*1600/(111320*Math.cos(p.lat*Math.PI/180));p.age+=dt*25;
            const b=this.map.latLngToContainerPoint([p.lat,p.lon]);
            const speed=Math.hypot(...vector);ctx.strokeStyle=speed>12?'rgba(255,186,100,.85)':'rgba(152,224,255,.65)';
            ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();
        }
        this.frame=requestAnimationFrame(this.tick);
    }
    remove(){this.stopped=true;cancelAnimationFrame(this.frame);this.map.off('moveend resize',this.reset);this.canvas.remove();}
}
