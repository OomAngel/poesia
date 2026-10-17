// Fetch URLs from inside the already-open loc.gov tab of Angel's Chrome (CDP on 127.0.0.1:9222),
// so the requests carry the session that passed Cloudflare. Usage: node cdp_fetch.mjs urls.json outdir
// urls.json: [{"url": "...", "out": "name.json", "binary": false}, ...]. Waits 2 s between requests.
import fs from "node:fs";
const [, , listFile, outDir] = process.argv;
const items = JSON.parse(fs.readFileSync(listFile, "utf8"));
const tabs = await (await fetch("http://127.0.0.1:9222/json/list")).json();
const tab = tabs.find(t => t.type === "page" && t.url.startsWith("https://www.loc.gov/"));
if (!tab) { console.error("no loc.gov tab open"); process.exit(1); }
const ws = new WebSocket(tab.webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener("open", r));
let id = 0; const pending = new Map();
ws.addEventListener("message", ev => { const m = JSON.parse(ev.data); if (pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
const call = (method, params) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
for (const it of items) {
  const dest = `${outDir}/${it.out}`;
  if (fs.existsSync(dest) && fs.statSync(dest).size > 0) { console.log("skip", it.out); continue; }
  const expr = it.binary
    ? `fetch(${JSON.stringify(it.url)}).then(async r => [r.status, btoa(String.fromCharCode(...new Uint8Array(await r.arrayBuffer())).slice(0)), r.headers.get('content-type')])`
    : `fetch(${JSON.stringify(it.url)}, {headers:{Accept:'application/json'}}).then(async r => [r.status, await r.text(), r.headers.get('content-type')])`;
  const res = await call("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true });
  const v = res.result?.result?.value;
  if (!Array.isArray(v)) { console.log("ERR", it.out, JSON.stringify(res.result?.exceptionDetails ?? res).slice(0, 300)); await new Promise(r => setTimeout(r, 5000)); continue; }
  const [status, body, ctype] = v;
  if (status === 200) fs.writeFileSync(dest, it.binary ? Buffer.from(body, "base64") : body);
  console.log(status, ctype, it.out, it.binary ? "" : body.length);
  await new Promise(r => setTimeout(r, 2000));
}
ws.close();
