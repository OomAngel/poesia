/* Calaverita card: drawn on a canvas in the visitor's browser (no server, no image model).
   The PNG carries a machine-readable AI mark (EU AI Act art. 50): an XMP packet in an iTXt chunk
   with IPTC DigitalSourceType = trainedAlgorithmicMedia, plus the visible label on the card. */
(function () {
  "use strict";
  const W = 1080, H = 1350;
  const C = { paper: "#f6e7c8", ink: "#2a1730", title: "#6b1d3a", dim: "#6d5a62",
              rosa: "#e5407a", marigold: "#ff9f1c", teal: "#2fb3a5", violet: "#8a5cd6", line: "#b9a48a" };
  const FLAGS = [C.rosa, C.marigold, C.teal, C.violet];

  function papelPicado(ctx, y, h) {
    const n = 12, gap = 8, w = (W - gap * (n - 1)) / n;
    for (let i = 0; i < n; i++) {
      const x = i * (w + gap);
      ctx.fillStyle = FLAGS[i % 4];
      ctx.beginPath();
      ctx.moveTo(x, y); ctx.lineTo(x + w, y); ctx.lineTo(x + w, y + h * 0.78);
      for (let k = 9; k >= 0; k--) ctx.lineTo(x + (w * k) / 10, y + (k % 2 ? h : h * 0.78));
      ctx.closePath(); ctx.fill();
      ctx.save(); ctx.globalCompositeOperation = "destination-out";
      ctx.beginPath(); ctx.arc(x + w / 2, y + h * 0.42, 9, 0, Math.PI * 2); ctx.fill();
      for (let r = 0; r < 2; r++) for (let c = 0; c < 4; c++) {
        ctx.beginPath(); ctx.arc(x + w * (0.18 + c * 0.21), y + h * (0.16 + r * 0.5), 3, 0, Math.PI * 2); ctx.fill();
      }
      ctx.restore();
    }
  }

  function wrap(ctx, text, maxW) {
    const words = text.split(/\s+/), out = []; let cur = "";
    for (const w of words) {
      const t = cur ? cur + " " + w : w;
      if (ctx.measureText(t).width > maxW && cur) { out.push(cur); cur = w; } else cur = t;
    }
    if (cur) out.push(cur);
    return out;
  }

  async function fontsReady() {
    try {
      await Promise.all([
        document.fonts.load('64px "Alfa Slab One"'),
        document.fonts.load('italic 40px "Literata"'),
        document.fonts.load('24px "IBM Plex Mono"'),
      ]);
    } catch (e) { /* fall back to system fonts */ }
  }

  function draw(canvas, d) {
    const ctx = canvas.getContext("2d");
    canvas.width = W; canvas.height = H;
    ctx.fillStyle = C.paper; ctx.fillRect(0, 0, W, H);
    papelPicado(ctx, 0, 92);
    const pad = 84;
    ctx.fillStyle = C.title; ctx.font = '60px "Alfa Slab One", Georgia, serif'; ctx.textBaseline = "top";
    let y = 136;
    for (const l of wrap(ctx, d.title, W - 2 * pad)) { ctx.fillText(l, pad, y); y += 70; }
    y += 18;
    const lines = d.stanzas.reduce((a, s) => a + s.length, 0);
    const size = lines > 12 ? 34 : lines > 8 ? 40 : 46;
    ctx.fillStyle = C.ink; ctx.font = `italic ${size}px "Literata", Georgia, serif`;
    for (const st of d.stanzas) {
      for (const l of st) { for (const part of wrap(ctx, l, W - 2 * pad)) { ctx.fillText(part, pad, y); y += size * 1.32; } }
      y += size * 0.7;
    }
    // footer: label + address, always on the card
    ctx.strokeStyle = C.line; ctx.setLineDash([6, 6]); ctx.beginPath(); ctx.moveTo(pad, H - 170); ctx.lineTo(W - pad, H - 170); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = C.dim; ctx.font = '26px "Literata", Georgia, serif';
    let fy = H - 150;
    for (const l of wrap(ctx, d.label, W - 2 * pad)) { ctx.fillText(l, pad, fy); fy += 34; }
    ctx.font = '22px "IBM Plex Mono", monospace'; ctx.fillText(d.address, pad, H - 50);
  }

  // --- PNG iTXt (XMP) insertion -----------------------------------------------------------
  const CRC = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
  function crc32(bytes) { let c = 0xffffffff; for (let i = 0; i < bytes.length; i++) c = CRC[(c ^ bytes[i]) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; }
  function xmp(desc) {
    const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
    return '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>' +
      '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">' +
      '<rdf:Description rdf:about="" xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" xmlns:dc="http://purl.org/dc/elements/1.1/">' +
      '<Iptc4xmpExt:DigitalSourceType>http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia</Iptc4xmpExt:DigitalSourceType>' +
      `<dc:description><rdf:Alt><rdf:li xml:lang="x-default">${esc(desc)}</rdf:li></rdf:Alt></dc:description>` +
      '</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>';
  }
  function withXmp(png, desc) {
    const enc = new TextEncoder();
    const key = enc.encode("XML:com.adobe.xmp");
    const text = enc.encode(xmp(desc));
    const data = new Uint8Array(key.length + 5 + text.length);
    data.set(key, 0); // keyword, then NUL, compression flag 0, method 0, empty language tag NUL, empty translated keyword NUL
    data.set(text, key.length + 5);
    const type = enc.encode("iTXt");
    const body = new Uint8Array(type.length + data.length); body.set(type, 0); body.set(data, 4);
    const chunk = new Uint8Array(12 + data.length);
    const dv = new DataView(chunk.buffer);
    dv.setUint32(0, data.length); chunk.set(body, 4); dv.setUint32(8 + data.length, crc32(body));
    const ihdrEnd = 8 + 25; // signature + IHDR chunk (length 13 + 12)
    const out = new Uint8Array(png.length + chunk.length);
    out.set(png.subarray(0, ihdrEnd), 0); out.set(chunk, ihdrEnd); out.set(png.subarray(ihdrEnd), ihdrEnd + chunk.length);
    return out;
  }

  async function render(canvas, d) {
    await fontsReady();
    draw(canvas, d);
    const blob = await new Promise((res) => canvas.toBlob(res, "image/png"));
    if (!blob) throw new Error("toBlob failed");
    const png = new Uint8Array(await blob.arrayBuffer());
    return new Blob([withXmp(png, d.label)], { type: "image/png" });
  }

  window.CalavCard = { render, _withXmp: withXmp, _crc32: crc32 };
})();
