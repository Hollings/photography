fetch("photos.json").then(r=>r.json()).then(list=>{
  const g=document.getElementById("gallery");
  list.forEach(p=>{
    const a=document.createElement("a");a.href=p.url;a.target="_blank";
    const i=document.createElement("img");i.src=p.url;i.alt=p.title||"";i.loading="lazy";
    a.appendChild(i);g.appendChild(a);
  });
}).catch(e=>console.error("load failed",e));
