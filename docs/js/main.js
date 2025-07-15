// How many images to add each time the user reaches the bottom
const BATCH_SIZE = 10;

let photos = [];
let nextIndex = 0;
const gallery  = document.getElementById("gallery");
const sentinel = document.getElementById("sentinel");

fetch("photos.json")
  .then(r => r.json())
  .then(data => {
    photos = Array.isArray(data) ? data : Object.values(data);
    loadNextBatch();                       // initial render
    setupObserver();                       // start observing for lazy loading
  })
  .catch(e => console.error("Failed to load photos.json", e));

function setupObserver() {
  const observer = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting) {
      loadNextBatch();
    }
  }, { rootMargin: "200px" });             // pre‑fetch a bit before scrolling

  observer.observe(sentinel);
}

function loadNextBatch() {
  for (let i = 0; i < BATCH_SIZE && nextIndex < photos.length; i++, nextIndex++) {
    gallery.appendChild(createPhotoBlock(photos[nextIndex]));
  }
}

function createPhotoBlock(p) {
  const block = document.createElement("div");
  block.className = "photo";

  // image element
  const img = document.createElement("img");
  img.src      = p.url;                    // initial src is fine; browser handles fetch when visible
  img.alt      = p.title || p.name || "";
  img.loading  = "lazy";                   // native lazy loading
  img.decoding = "async";

  // wrap image in a link that opens in a new tab
  const link = document.createElement("a");
  link.href   = p.url;
  link.target = "_blank";
  link.rel    = "noopener";
  link.appendChild(img);

  // caption with metadata
  const caption = document.createElement("div");
  caption.className = "caption";
  caption.innerHTML = buildCaption(p);

  block.appendChild(link);
  block.appendChild(caption);
  return block;
}

function buildCaption(p) {
  const title    = p.title || p.name || "";
  const shutter  = formatShutter(p.shutter_speed);
  const iso      = p.iso ? `ISO ${p.iso}` : "";
  const aperture = extractAperture(p.lens);

  const exposure = [shutter, aperture ? `f/${aperture}` : null, iso]
                    .filter(Boolean)
                    .join(" | ");

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
