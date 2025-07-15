fetch("photos.json")
  .then(r => r.json())
  .then(data => {
    const photos  = Array.isArray(data) ? data : Object.values(data);
    const gallery = document.getElementById("gallery");

    photos.forEach(p => {
      const block = document.createElement("div");
      block.className = "photo";

      // image element
      const img = document.createElement("img");
      img.src   = p.url;
      img.alt   = p.title || p.name || "";

      // wrap image in a link that opens in a new tab
      const link = document.createElement("a");
      link.href   = p.url;
      link.target = "_blank";
      link.rel    = "noopener";          // security best-practice
      link.appendChild(img);

      // caption with metadata
      const caption = document.createElement("div");
      caption.className = "caption";
      caption.innerHTML = buildCaption(p);

      block.appendChild(link);           // clickable image
      block.appendChild(caption);
      gallery.appendChild(block);
    });
  })
  .catch(e => console.error("Failed to load photos.json", e));

function buildCaption(p) {
  const title    = p.title || p.name || "";
  const shutter  = formatShutter(p.shutter_speed);
  const iso      = p.iso ? `ISO ${p.iso}` : "";
  const aperture = extractAperture(p.lens);

  const exposure = [shutter, aperture ? `f/${aperture}` : null, iso]
                    .filter(Boolean)
                    .join(" | ");

  return `
    <span class="title">${title}</span><br>
    <span class="meta">${p.camera}<br>${p.lens}<br>${exposure}</span>
  `;
}

function formatShutter(s) {
  const val = parseFloat(s);
  if (!val) return "";
  if (val >= 1) return val + "s";
  return "1/" + Math.round(1 / val) + "s";
}

function extractAperture(lens) {
  const match = lens && lens.match(/F(\d+\.?\d*)/i);
  return match ? match[1] : "";
}
