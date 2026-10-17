/* PoesIA · Calaveritas: page logic. No cookies, no storage, no analytics; the form goes to
   /api/calaverita once and the answer is shown, copied, shared or drawn as a card here. */
(function () {
  "use strict";
  const LANG = document.documentElement.lang === "en" ? "en" : "es";
  const TABS = ["crear", "que", "tonos", "como", "aviso"];
  const PRIVATE = ["amistad", "familia", "pareja", "trabajo"];
  const RECIPIENTS = ["amistad", "familia", "pareja", "trabajo", "publica", "mascota", "yo", "fallecida"];
  const TONES = ["carinosa", "picara", "politica", "escolar", "clasica"];
  const TRAITS = {
    tarde: ["siempre llega tarde", "always late"], cafe: ["vive de café", "runs on coffee"],
    plantas: ["colecciona plantas", "collects plants"], celular: ["no suelta el celular", "glued to the phone"],
    chismes: ["sabe todos los chismes", "knows all the gossip"], cocina: ["cocina de maravilla", "a great cook"],
    futbol: ["fanático del futbol", "football fanatic"], dormir: ["duerme a todas horas", "sleeps all the time"],
    baile: ["no para de bailar", "never stops dancing"], series: ["ve series sin parar", "binge-watches series"],
    deporte: ["vive en el gimnasio", "lives at the gym"], musica: ["canta a todas horas", "always singing"],
    ahorro: ["no gasta un peso", "never spends a penny"], compras: ["compra de todo", "buys everything"],
    mascotas: ["ama a sus mascotas", "loves their pets"], viajes: ["siempre de viaje", "always travelling"],
  };
  const T = {
    es: {
      tabs: ["Crear", "¿Qué es una calaverita?", "Tonos", "Cómo funciona", "Aviso y privacidad"],
      kicker: "Día de Muertos · 1 y 2 de noviembre",
      h1: "Pide una calaverita para quien tú quieras",
      lede: "Tú das el nombre y unas manías; la IA escribe los versos y PoesIA revisa la métrica y la rima de cada uno.",
      whoL: "¿Para quién?",
      whoPriv: "Solo el nombre de pila (una o dos palabras).", whoOther: "Nombre, apodo o personaje público.",
      relL: "¿Quién es para ti?",
      rel: ["Amistad", "Familia", "Pareja", "Trabajo", "Persona pública", "Mascota", "Yo mismo/a", "Famoso/a fallecido/a"],
      ageL: "Tu año de nacimiento", ageH: "No se guarda.", ageChoose: "Elige…",
      traitsL: "Sus manías (hasta 4)", traitsH: "Toca para elegir.",
      detailL: "Un detalle más (opcional)", detailPh: "Ej.: siempre pide la cuenta dividida",
      toneL: "Tono", toneMore: "¿Qué es cada tono?",
      tones: [["Cariñosa", "Para alguien querido: la Muerte se lo lleva con ternura y humor suave."],
              ["Pícara", "Se ríe de sus manías sin piedad, pero sin crueldad y sin nada sexual."],
              ["Política", "La tradición de la prensa satírica: burla del papel público, no de la vida privada."],
              ["Escolar", "Apta para el salón de clases: sin groserías, alcohol, drogas ni violencia."],
              ["Clásica", "Al estilo de las hojas volantes de Vanegas Arroyo y Posada, con tono de pregón."]],
      lenL: "Estrofas",
      consentPriv: "Es para alguien a quien le daría risa. Entiendo que es sátira escrita por IA y soy responsable de cómo la comparto.",
      consent: "Entiendo que es sátira escrita por IA y que soy responsable de cómo la comparto.",
      contest: "Para jugar y regalar, no para concursos: muchos concursos prohíben textos escritos con IA.",
      go: "Escribir mi calaverita",
      eName: "Falta el nombre.", eAge: "Elige tu año de nacimiento.", eOk: "Marca la casilla para continuar.",
      eNet: "No hubo respuesta. Revisa tu conexión e intenta de nuevo.",
      writingH: "La Catrina está escribiendo…",
      steps: ["Buscando las rimas…", "Contando sílabas…", "Revisando cada verso…", "Puliendo el remate…"],
      cancel: "Cancelar",
      title: (n) => `Calaverita para ${n}`,
      scheme: (s) => `Rima ${s} · octosílabos · sílabas por verso a la derecha`,
      label: (m) => `Calaverita escrita con IA (${m}) y revisada por PoesIA. Es sátira y ficción: no afirma hechos sobre personas reales.`,
      share: "Compartir", dl: "Descargar tarjeta", copy: "Copiar texto", again: "Otra versión", rep: "Reportar", restart: "Empezar de nuevo",
      copied: "Copiado, con la etiqueta de IA incluida.", copyFail: "No se pudo copiar: selecciona el poema a mano.",
      shareFail: "Tu navegador no comparte imágenes: usa «Descargar tarjeta».", cardFail: "No se pudo dibujar la tarjeta; copia el texto.",
      inapp: "Si estás dentro de Instagram o Facebook, abre la página en tu navegador para descargar.",
      repL: "¿Qué tiene de malo esta calaverita? (opcional)", repSend: "Enviar reporte", repDone: "Gracias: el reporte llegó.",
      queH: "¿Qué es una calaverita?",
      que1: "Una calaverita (o calavera literaria) es un poema breve y burlón que en México se escribe para el Día de Muertos. En él, la Muerte viene a llevarse a alguien vivo y, de paso, se ríe de sus manías, sus defectos o su poder.",
      que2: "Nacieron en la prensa satírica del siglo XIX como epitafios de broma para políticos y personajes conocidos. A principios del siglo XX, la imprenta de Antonio Vanegas Arroyo las publicaba en hojas sueltas ilustradas por José Guadalupe Posada, que grabó la famosa calavera elegante con sombrero; décadas después Diego Rivera la llamó «La Catrina».",
      que3: "Hoy se escriben cada noviembre en escuelas, periódicos y redes, para amistades, familia, colegas y políticos.",
      queFormH: "La forma",
      queForm: "Lo más común son cuartetas de versos de ocho sílabas que riman ABAB o ABBA. La Muerte llega por alguien, se burla de sus rasgos y cierra con un remate que sorprenda. Los ejemplos que guían al modelo son calaveras clásicas de dominio público de la imprenta de Vanegas Arroyo (1903-1913).",
      tonosH: "Los tonos",
      tonosP: "El tono decide de qué y cómo se ríe la Catrina. Ninguno cambia la forma. Las calaveritas tradicionales son humor adulto, así que a menores de 18 años solo se les ofrece el tono Escolar.",
      comoH: "Cómo funciona",
      stepsL: [["Tú das los datos", "Un nombre, quién es para ti, unas manías, el tono y cuántas estrofas."],
               ["La IA propone los versos", "Apertus, un modelo de lenguaje abierto hecho en Suiza, escribe la calaverita estrofa por estrofa en los servidores de CSCS (Suiza)."],
               ["PoesIA revisa", "Cuenta las sílabas de cada verso, comprueba la rima y descarta lo que no cumple, antes de mostrártelo."],
               ["Tú la compartes", "Comparte la tarjeta, descárgala o copia el texto. La etiqueta de IA viaja con ella."]],
      marksH: "Cómo reconocer que la escribió una IA",
      marks: "Cada calaverita lleva la etiqueta visible «escrita con IA». La tarjeta PNG lleva además una marca legible por máquina (metadatos XMP con el código IPTC «trainedAlgorithmicMedia»), y en esta página el poema está marcado como generado por IA en el código.",
      limitsH: "Límites",
      limits: "Para que el sitio siga abierto para todos hay un número máximo de calaveritas por persona y por día. Si el modelo no responde, el sitio te lo dice en lugar de inventar.",
      avisoH: "Aviso y privacidad",
      satH: "Es sátira",
      sat: "Las calaveritas son un género satírico. Los textos los genera un modelo de IA: pueden equivocarse u ofender, no afirman hechos sobre personas reales y no expresan opiniones de este sitio. Quien la pide es responsable de cómo la comparte.",
      floorH: "Lo que no se escribe",
      floor: "Cualquier tema y cualquier persona, también públicas. No se escriben amenazas, datos personales como domicilios, teléfonos o correos, contenido sexual, discurso de odio, acusaciones de hechos, ni datos de salud, religión o sexualidad de personas privadas.",
      privH: "Privacidad",
      priv: "No guardamos nombres ni poemas y no usamos cookies. Para escribir la calaverita, los datos del formulario se envían una vez al modelo Apertus en CSCS (Suiza) y se descartan. Si CSCS no responde, otro servidor escribe la calaverita sin recibir el nombre: el nombre lo pone esta página. Los reportes se envían a un buzón privado (GitHub) con el texto reportado. Los registros técnicos solo cuentan peticiones, sin nombres ni textos.",
      contH: "Contacto y retiradas",
      cont: "Escribe a través de GitHub: github.com/OomAngel. Para pedir que se retire algo, usa «Reportar» o escribe ahí con el texto.",
      fShort: "Sátira escrita con IA. No afirma hechos sobre personas reales.",
      fMade: "PoesIA: poesía con IA y métrica revisada. Calaveritas es su primera sección. Hecho con Apertus.",
    },
    en: {
      tabs: ["Create", "What is a calaverita?", "Tones", "How it works", "Notice and privacy"],
      kicker: "Day of the Dead · 1 and 2 November",
      h1: "Get a calaverita for anyone you like",
      lede: "You give a name and a few quirks; the AI writes the verses, and PoesIA checks the metre and the rhyme of every line.",
      whoL: "Who is it for?",
      whoPriv: "First name only (one or two words).", whoOther: "A name, a nickname or a public figure.",
      relL: "Who are they to you?",
      rel: ["Friend", "Family", "Partner", "Work", "Public figure", "Pet", "Myself", "Late famous person"],
      ageL: "Your year of birth", ageH: "Not stored.", ageChoose: "Choose…",
      traitsL: "Their quirks (up to 4)", traitsH: "Tap to choose.",
      detailL: "One more detail (optional)", detailPh: "E.g. always splits the bill",
      toneL: "Tone", toneMore: "What does each tone mean?",
      tones: [["Affectionate", "For someone dear: Death takes them gently, with soft humour."],
              ["Cheeky", "Mocks their quirks without mercy, but without cruelty and nothing sexual."],
              ["Political", "The satirical-press tradition: mocking the public role, not private life."],
              ["School", "Fit for the classroom: no swearing, alcohol, drugs or violence."],
              ["Classic", "In the style of the old Vanegas Arroyo and Posada broadsides, like a street crier."]],
      lenL: "Stanzas",
      consentPriv: "It is for someone who would laugh at it. I understand this is AI-written satire and I am responsible for how I share it.",
      consent: "I understand this is AI-written satire and that I am responsible for how I share it.",
      contest: "For fun and gifts, not for contests: many contests forbid AI-written entries.",
      go: "Write my calaverita",
      eName: "Add a name.", eAge: "Choose your year of birth.", eOk: "Tick the box to continue.",
      eNet: "No answer came back. Check your connection and try again.",
      writingH: "The Catrina is writing…",
      steps: ["Finding the rhymes…", "Counting syllables…", "Checking every line…", "Polishing the punchline…"],
      cancel: "Cancel",
      title: (n) => `A calaverita for ${n}`,
      scheme: (s) => `Rhyme ${s} · four beats, about eight syllables · syllables per line on the right`,
      label: (m) => `Calaverita written with AI (${m}) and checked by PoesIA. It is satire and fiction: it states no facts about real people.`,
      share: "Share", dl: "Download card", copy: "Copy text", again: "Another version", rep: "Report", restart: "Start over",
      copied: "Copied, with the AI label included.", copyFail: "Could not copy: select the poem by hand.",
      shareFail: "Your browser cannot share images: use “Download card”.", cardFail: "The card could not be drawn; copy the text instead.",
      inapp: "If you are inside Instagram or Facebook, open the page in your browser to download.",
      repL: "What is wrong with this calaverita? (optional)", repSend: "Send report", repDone: "Thank you: the report arrived.",
      queH: "What is a calaverita?",
      que1: "A calaverita (or literary calavera) is a short, teasing poem written in Mexico for the Day of the Dead. In it, Death comes to take someone who is still alive and, along the way, mocks their habits, their flaws or their power.",
      que2: "They began in the satirical press of the nineteenth century as mock epitaphs for politicians and well-known figures. In the early twentieth century the press of Antonio Vanegas Arroyo printed them on broadsides illustrated by José Guadalupe Posada, who engraved the famous elegant skeleton in a hat; decades later Diego Rivera named her “La Catrina”.",
      que3: "Today they are written every November in schools, newspapers and on social media, for friends, family, colleagues and politicians.",
      queFormH: "The form",
      queForm: "In Spanish the usual form is four-line stanzas of eight-syllable lines rhyming ABAB or ABBA. In English this site uses four-beat lines with the same rhymes. Death comes for someone, teases their traits and ends with a surprising twist. The examples that guide the model are public-domain classic calaveras from the Vanegas Arroyo press (1903-1913).",
      tonosH: "The tones",
      tonosP: "The tone decides what the Catrina laughs at, and how. None of them changes the form. Traditional calaveritas are adult humour, so under-18s are offered the School tone only.",
      comoH: "How it works",
      stepsL: [["You give the details", "A name, who they are to you, a few quirks, the tone and how many stanzas."],
               ["The AI drafts the verses", "Apertus, an open language model made in Switzerland, writes the calaverita stanza by stanza on CSCS servers (Switzerland)."],
               ["PoesIA checks them", "It counts the syllables of every line, checks the rhyme and discards what fails, before you see it."],
               ["You share it", "Share the card, download it or copy the text. The AI label travels with it."]],
      marksH: "How to tell it was written by AI",
      marks: "Every calaverita carries the visible label “written with AI”. The PNG card also carries a machine-readable mark (XMP metadata with the IPTC code “trainedAlgorithmicMedia”), and on this page the poem is marked as AI-generated in the code.",
      limitsH: "Limits",
      limits: "To keep the site open for everyone there is a maximum number of calaveritas per person per day. If the model does not answer, the site says so instead of making something up.",
      avisoH: "Notice and privacy",
      satH: "It is satire",
      sat: "Calaveritas are a satirical genre. The texts are written by an AI model: they can be wrong or offensive, they state no facts about real people and they express no opinions of this site. Whoever requests one is responsible for how they share it.",
      floorH: "What is not written",
      floor: "Any topic and any person, public figures included. Not written: threats, personal data such as home addresses, phone numbers or e-mail, sexual content, hate speech, factual allegations, and health, religion or sexuality details of private people.",
      privH: "Privacy",
      priv: "We do not store names or poems and use no cookies. To write the calaverita, the form's details are sent once to the Apertus model at CSCS (Switzerland) and discarded. If CSCS does not answer, another server writes the calaverita without receiving the name: this page puts the name in. Reports go to a private inbox (GitHub) with the reported text. Technical logs only count requests, with no names or texts.",
      contH: "Contact and takedowns",
      cont: "Write through GitHub: github.com/OomAngel. To ask for something to be taken down, use “Report” or write there with the text.",
      fShort: "AI-written satire. It states no facts about real people.",
      fMade: "PoesIA: poetry with AI and checked metre. Calaveritas is its first section. Made with Apertus.",
    },
  };
  const t = T[LANG];
  const $ = (id) => document.getElementById(id);
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const state = { rel: "amistad", tone: "picara", len: 3, traits: [], tab: "crear", result: null, blob: null, payload: null, ctrl: null };

  const age = () => { const y = parseInt($("byear").value, 10); return y ? new Date().getFullYear() - y : null; };
  const minor = () => { const a = age(); return a !== null && a < 18; };

  function flags(el, n) { el.textContent = ""; for (let i = 0; i < n; i++) { const d = document.createElement("div"); d.className = "flag"; el.appendChild(d); } }

  function chip(label, pressed, cls, onClick, disabled) {
    const b = document.createElement("button"); b.type = "button"; b.className = "chip " + (cls || ""); b.textContent = label;
    b.setAttribute("aria-pressed", String(pressed)); if (disabled) b.disabled = true; b.addEventListener("click", onClick); return b;
  }

  function showTab(name) {
    state.tab = name;
    document.querySelectorAll("[data-tab]").forEach((s) => { s.hidden = s.dataset.tab !== name; });
    if (name === "crear") { const has = !!state.result; $("resultView").hidden = !has; $("formView").hidden = has; $("writeView").hidden = true; }
    [...$("tabs").children].forEach((b, i) => b.setAttribute("aria-selected", String(TABS[i] === name)));
    window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
  }

  function renderForm() {
    const isPriv = PRIVATE.includes(state.rel);
    if (minor()) { if (state.tone !== "escolar") state.tone = "escolar"; if (state.rel === "pareja") state.rel = "amistad"; }
    $("whoH").textContent = isPriv ? t.whoPriv : t.whoOther;
    const rel = $("rel"); rel.textContent = "";
    RECIPIENTS.forEach((r, i) => rel.appendChild(chip(t.rel[i], r === state.rel, "", () => { state.rel = r; renderForm(); }, minor() && r === "pareja")));
    const tr = $("traits"); tr.textContent = "";
    Object.entries(TRAITS).forEach(([id, lab]) => tr.appendChild(chip(lab[LANG === "es" ? 0 : 1], state.traits.includes(id), "len", () => {
      if (state.traits.includes(id)) state.traits = state.traits.filter((x) => x !== id);
      else if (state.traits.length < 4) state.traits.push(id);
      renderForm();
    })));
    const max = isPriv ? 80 : 200; const d = $("detail"); d.maxLength = max; if (d.value.length > max) d.value = d.value.slice(0, max);
    $("detailCount").textContent = `${d.value.length}/${max}`;
    const tone = $("tone"); tone.textContent = "";
    TONES.forEach((x, i) => tone.appendChild(chip(t.tones[i][0], x === state.tone, "tone", () => { state.tone = x; renderForm(); }, minor() && x !== "escolar")));
    $("tonehint").textContent = t.tones[TONES.indexOf(state.tone)][1];
    const len = $("len"); len.textContent = "";
    [1, 2, 3, 4].forEach((n) => len.appendChild(chip(String(n), n === state.len, "len", () => { state.len = n; renderForm(); })));
    $("consentText").textContent = isPriv ? t.consentPriv : t.consent;
  }

  function renderStatic() {
    document.querySelectorAll("[data-i]").forEach((el) => { const v = t[el.dataset.i]; if (typeof v === "string") el.textContent = v; });
    $("lang-" + LANG).setAttribute("aria-current", "page");
    $("detail").placeholder = t.detailPh;
    const tabs = $("tabs"), fn = $("footnav"); tabs.textContent = ""; fn.textContent = "";
    t.tabs.forEach((label, i) => {
      const b = document.createElement("button"); b.type = "button"; b.setAttribute("role", "tab"); b.textContent = label;
      b.addEventListener("click", () => showTab(TABS[i])); tabs.appendChild(b);
      const a = document.createElement("button"); a.type = "button"; a.className = "linkish"; a.textContent = label; a.addEventListener("click", () => showTab(TABS[i])); fn.appendChild(a);
    });
    document.querySelectorAll("[data-goto]").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.goto)));
    const tl = $("tonelist"); tl.textContent = "";
    t.tones.forEach(([n, d]) => { const x = document.createElement("div"); const b = document.createElement("b"); b.textContent = n; const p = document.createElement("p"); p.textContent = d; x.append(b, p); tl.appendChild(x); });
    const st = $("steps"); st.textContent = "";
    t.stepsL.forEach(([h, d]) => { const li = document.createElement("li"); const w = document.createElement("div"); const b = document.createElement("b"); b.textContent = h; const p = document.createElement("div"); p.className = "hint"; p.textContent = d; w.append(b, p); li.appendChild(w); st.appendChild(li); });
    $("cont").textContent = t.cont;
    const by = $("byear"); const y0 = new Date().getFullYear();
    const o0 = document.createElement("option"); o0.value = ""; o0.textContent = t.ageChoose; by.appendChild(o0);
    for (let y = y0; y >= 1920; y--) { const o = document.createElement("option"); o.value = String(y); o.textContent = String(y); by.appendChild(o); }
    by.addEventListener("change", renderForm);
    $("detail").addEventListener("input", renderForm);
    flags($("picadoTop"), 16); flags($("picadoCard"), 12);
  }

  function payload() {
    return { language: LANG, name: $("who").value.trim(), recipient: state.rel, tone: state.tone, stanzas: state.len,
             traits: state.traits, detail: $("detail").value.trim(), birth_year: parseInt($("byear").value, 10) };
  }

  let stepTimer = null;
  function writing(on) {
    $("formView").hidden = on || !!state.result; $("writeView").hidden = !on; if (on) $("resultView").hidden = true;
    clearInterval(stepTimer); $("cancel").hidden = true;
    if (on) {
      let i = 0; $("wstatus").textContent = t.steps[0];
      stepTimer = setInterval(() => { i = (i + 1) % t.steps.length; $("wstatus").textContent = t.steps[i]; if (i === 2) $("cancel").hidden = false; }, 3000);
    }
  }

  async function submit(body) {
    state.payload = body; state.ctrl = new AbortController(); writing(true);
    try {
      const res = await fetch("/api/calaverita", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal: state.ctrl.signal });
      const data = await res.json().catch(() => ({}));
      writing(false);
      if (!res.ok || !data.ok) { state.result = null; $("formView").hidden = false; $("err").textContent = data.message || t.eNet; return; }
      state.result = data; showResult();
    } catch (e) {
      writing(false); $("formView").hidden = false; $("err").textContent = e.name === "AbortError" ? "" : t.eNet;
    }
  }

  function poemText() {
    const r = state.result; const label = t.label(r.poem.model);
    return `${t.title(r.name)}\n\n${r.poem.stanzas.map((s) => s.lines.join("\n")).join("\n\n")}\n\n${label}\n${location.host}`;
  }

  function showResult() {
    const r = state.result;
    $("formView").hidden = true; $("resultView").hidden = false; $("toast").textContent = ""; $("reportbox").hidden = true;
    $("cardTitle").textContent = t.title(r.name);
    const schemes = [...new Set(r.poem.stanzas.map((s) => s.scheme))].join(" / ");
    $("scheme").textContent = t.scheme(schemes);
    const p = $("poem"); p.textContent = ""; p.lang = r.poem.language;
    r.poem.stanzas.forEach((s) => {
      const div = document.createElement("div"); div.className = "stanza";
      s.lines.forEach((l, i) => {
        const row = document.createElement("div"); row.className = "vl";
        const span = document.createElement("span"); span.textContent = l;
        const m = document.createElement("span"); m.className = "m" + (s.syllables[i] === r.poem.target_syllables ? "" : " off"); m.textContent = String(s.syllables[i]);
        row.append(span, m); div.appendChild(row);
      });
      p.appendChild(div);
    });
    $("ailabel").textContent = t.label(r.poem.model);
    $("brandmark").textContent = location.host;
    $("card").dataset.aiModel = r.poem.model;
    state.blob = null;
    window.CalavCard.render($("cardCanvas"), { title: t.title(r.name), stanzas: r.poem.stanzas.map((s) => s.lines), label: t.label(r.poem.model), address: location.host })
      .then((b) => { state.blob = b; }).catch(() => { $("toast").textContent = t.cardFail; });
    $("card").scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  }

  function cardFile() { return new File([state.blob], "calaverita.png", { type: "image/png" }); }

  function download() {
    if (!state.blob) { $("toast").textContent = t.cardFail; return; }
    const a = document.createElement("a"); a.href = URL.createObjectURL(state.blob); a.download = "calaverita.png";
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    if (/Instagram|FBAN|FBAV/.test(navigator.userAgent)) $("toast").textContent = t.inapp;
  }

  $("f").addEventListener("submit", (e) => {
    e.preventDefault();
    if (!$("who").value.trim()) { $("err").textContent = t.eName; $("who").focus(); return; }
    if (!$("byear").value) { $("err").textContent = t.eAge; $("byear").focus(); return; }
    if (!$("ok").checked) { $("err").textContent = t.eOk; $("ok").focus(); return; }
    $("err").textContent = ""; state.result = null; submit(payload());
  });
  $("cancel").addEventListener("click", () => { if (state.ctrl) state.ctrl.abort(); });
  $("again").addEventListener("click", () => { if (state.payload) { state.result = null; submit(state.payload); } });
  $("restart").addEventListener("click", () => { state.result = null; $("resultView").hidden = true; $("formView").hidden = false; $("who").focus(); });
  $("copy").addEventListener("click", () => {
    const done = () => { $("toast").textContent = t.copied; };
    const fail = () => { $("toast").textContent = t.copyFail; const rg = document.createRange(); rg.selectNodeContents($("card")); const s = getSelection(); s.removeAllRanges(); s.addRange(rg); };
    try { navigator.clipboard.writeText(poemText()).then(done, fail); } catch (e) { fail(); }
  });
  $("share").addEventListener("click", () => {
    if (!state.blob) { $("toast").textContent = t.cardFail; return; }
    const file = cardFile();
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      navigator.share({ files: [file], text: poemText() }).catch(() => {});
    } else { $("toast").textContent = t.shareFail; }
  });
  $("dl").addEventListener("click", download);
  $("rep").addEventListener("click", () => { $("reportbox").hidden = false; $("reason").focus(); });
  $("repSend").addEventListener("click", async () => {
    try {
      const res = await fetch("/api/report", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: LANG, poem: poemText(), reason: $("reason").value.trim() }) });
      const data = await res.json().catch(() => ({}));
      $("toast").textContent = data.ok ? t.repDone : (data.message || t.eNet);
      if (data.ok) $("reportbox").hidden = true;
    } catch (e) { $("toast").textContent = t.eNet; }
  });

  renderStatic(); renderForm(); showTab("crear");
})();
