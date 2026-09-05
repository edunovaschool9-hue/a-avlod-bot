// EduNova maktab boti v2 — o'qituvchi / admin / direktor + ota-ona xabarlari
const TEACH = Deno.env.get("TEACH_TOKEN") ?? "";
const OTA   = Deno.env.get("TG_TOKEN") ?? "";
const CRON  = Deno.env.get("CRON_KEY") ?? "";
const SBURL = Deno.env.get("SUPABASE_URL") ?? "";
const SBKEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
const SAYT  = "https://edunovaschool9-hue.github.io/a-avlod-bot/";
const APP   = SAYT + "app.html";
const FN    = () => `${SBURL}/functions/v1/teach-bot`;

const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "content-type, authorization, apikey", "Access-Control-Allow-Methods": "POST, GET, OPTIONS" };
const jsonc = (o: unknown, status = 200) => new Response(JSON.stringify(o), { status, headers: { ...CORS, "Content-Type": "application/json" } });
const no = () => new Response("no", { status: 403, headers: CORS });

async function rpc(fn: string, args: Record<string, unknown>) {
  const r = await fetch(`${SBURL}/rest/v1/rpc/${fn}`, { method: "POST",
    headers: { "Content-Type": "application/json", apikey: SBKEY, Authorization: `Bearer ${SBKEY}` }, body: JSON.stringify(args) });
  if (!r.ok) { console.error("rpc", fn, r.status, (await r.text()).slice(0, 120)); return null; }
  const t = await r.text(); try { return JSON.parse(t); } catch { return t; }
}
async function tg(method: string, body: Record<string, unknown>, token = TEACH) {
  const r = await fetch(`https://api.telegram.org/bot${token}/${method}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json(); if (!j?.ok) console.error(method, JSON.stringify(j).slice(0, 160)); return j;
}
const send = (chat_id: number, text: string, extra: Record<string, unknown> = {}, token = TEACH) =>
  tg("sendMessage", { chat_id, text, parse_mode: "HTML", ...extra }, token);
const esc = (s: unknown) => String(s ?? "").replace(/[<>&]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c] as string));
const cronOk = async (k: string | null) => !!k && ((CRON && k === CRON) || (await rpc("ep_cron_ok", { p_kalit: k })) === true);

// ---------- klaviaturalar ----------
const KB_LOK = { keyboard: [[{ text: "📍 Joylashuvni yuborish", request_location: true }]], resize_keyboard: true, one_time_keyboard: true };
const KB_ADMIN = { keyboard: [[{ text: "🏫 Kim maktabda" }, { text: "📋 Davomat hisoboti" }], [{ text: "📣 Chaqirish" }, { text: "📝 Arizalar" }], [{ text: "👨‍👩‍👧 Ota-onalar" }, { text: "📢 Xabar" }], [{ text: "🎒 O‘quvchilar" }, { text: "🎫 Talonlar" }], [{ text: "📝 Xulosalar" }, { text: "👩‍🏫 O‘qituvchilar" }], [{ text: "📤 Davomat so‘rash" }], [{ text: "📱 Kabinet" }]], resize_keyboard: true };
const KB_TEACH = { keyboard: [[{ text: "✅ Davomat belgilash" }, { text: "📝 Xulosa yozish" }], [{ text: "📍 Joylashuvni yuborish", request_location: true }], [{ text: "📊 Holatim" }, { text: "📱 Kabinet" }]], resize_keyboard: true };
const KB_APP = (t = "📱 Kabinetni ochish") => ({ inline_keyboard: [[{ text: t, web_app: { url: APP } }]] });

const T = {
  salom: "Assalomu alaykum! Bu — <b>EduNova School</b> boti.\n\nO‘qituvchi bo‘lsangiz — <b>ism va familiyangizni</b> bitta xabarda yozing.\nRahbariyat bo‘lsangiz — /admin",
  tel: "Rahmat! Endi telefon raqamingizni yozing.\n\nMasalan: <i>+998 90 123 45 67</i>",
  kutilmoqda: "Arizangiz qabul qilindi ✅\nAdministrator tasdiqlagach, bot sizga PIN kod va kabinet havolasini yuboradi.",
  ism_xato: "Ism va familiyani to‘liq yozing — ikki so‘z bilan.\nMasalan: <i>Aliyev Sardor</i>",
  tel_xato: "Telefon raqamini to‘liq yozing.\nMasalan: <i>+998 90 123 45 67</i>",
  tasdiq: (pin: string) => `Tabriklaymiz! Siz tasdiqlandingiz ✅\n\n<b>PIN kodingiz: ${pin}</b>\nKabinet: ${SAYT}oqituvchi-kabinet.html\n\n<b>Davomat:</b> har kuni ertalab 📎 → Geolokatsiya → <b>Translatsiya</b> → 8 soat.`,
  rad: "Arizangiz tasdiqlanmadi. Administrator bilan bog‘laning.",
  royxatda_yoq: "Siz hali tasdiqlanmagansiz. Administrator tasdiqlashini kuting.",
  admin_pin: "Rahbariyat kirishi. <b>Admin PIN kodingizni</b> yozing.",
  admin_ok: (ism: string) => `Xush kelibsiz, <b>${esc(ism)}</b>! Rahbariyat menyusi ochildi.`,
  admin_xato: "PIN noto‘g‘ri.",
  eslatma: "Xayrli tong! Davomat uchun jonli joylashuvni yoqing:\n📎 → Geolokatsiya → <b>Translatsiya</b> → 8 soat.",
  maktab_ok: (lat: number, lon: number, r: number) => `Maktab nuqtasi saqlandi ✅\n${lat.toFixed(5)}, ${lon.toFixed(5)} · radius ${r} m`,
};

// ---------- matn tuzuvchilar ----------
const HOLAT_BELGI: Record<string, string> = { ichkarida: "🟢", tashqarida: "🟠", ketdi: "🔴", yoq: "⚪" };
async function kimMaktabda(): Promise<string> {
  const d = await rpc("ep_teach_hozir", {});
  if (!d?.ok) return "Xatolik";
  if (!d.maktab) return "⚠️ Maktab nuqtasi o‘rnatilmagan — /maktab buyrug‘i bilan hovlida turib joylashuv yuboring.";
  const r: any[] = d.royxat ?? [];
  const ich = r.filter((x: any) => x.holat === "ichkarida");
  let t = `🏫 <b>Kim maktabda</b> · ${d.kun}\n<b>${ich.length}</b> / ${r.length} o‘qituvchi ichkarida\n`;
  const gr = (nom: string, list: any[]) => { if (!list.length) return; t += `\n<b>${nom}</b>\n`; list.forEach((x: any) => {
    t += `${HOLAT_BELGI[x.holat] ?? "⚪"} ${esc(x.ism)}` + (x.keldi ? ` · keldi ${x.keldi}` : "") + (x.ketdi ? ` · ketdi ${x.ketdi}` : "") + (x.holat === "tashqarida" && x.masofa ? ` · ${x.masofa} m` : "") + "\n"; }); };
  gr("Ichkarida", ich); gr("Tashqarida", r.filter((x: any) => x.holat === "tashqarida"));
  gr("Ketgan / joylashuv to‘xtagan", r.filter((x: any) => x.holat === "ketdi")); gr("Joylashuv yo‘q", r.filter((x: any) => x.holat === "yoq"));
  return t;
}
async function davomatMatn(ismlar = false): Promise<string> {
  const d = await rpc("ep_dav_xulosa", { p_kun: null });
  if (!d?.ok) return "Xatolik";
  let t = `📋 <b>O‘quvchilar davomati</b> · ${d.kun}\n✅ Keldi: <b>${d.keldi + d.kech}</b>` + (d.kech ? ` (${d.kech} kech)` : "") +
    `   ❌ Kelmadi: <b>${d.kelmadi}</b>\n⚪ Belgilanmagan: ${d.jami - d.keldi - d.kech - d.kelmadi}   · jami ${d.jami}\n\n`;
  (d.sinflar ?? []).forEach((s: any) => {
    if (!s.jami) return;
    t += `<b>${s.nom}</b> ${s.keldi}/${s.jami}` + (s.kelmadi ? ` · ❌${s.kelmadi}` : "") + "\n";
    if (ismlar && s.kelmaganlar) t += `   <i>${esc(s.kelmaganlar)}</i>\n`;
  });
  return t;
}

// ---------- admin menyusi ----------
async function adminMenyu(chat: number, ism: string) {
  await tg("setChatMenuButton", { chat_id: chat, menu_button: { type: "web_app", text: "Kabinet", web_app: { url: APP } } });
  await send(chat, T.admin_ok(ism), { reply_markup: KB_ADMIN });
}
async function chaqirishRoyxat(chat: number) {
  const d = await rpc("ep_teach_hozir", {});
  const r: any[] = ((d?.royxat ?? []) as any[]).filter((x: any) => x.tg);
  if (!r.length) { await send(chat, "Telegramga ulangan o‘qituvchi yo‘q."); return; }
  const rows = r.map((x: any) => [{ text: `${HOLAT_BELGI[x.holat] ?? "⚪"} ${x.ism}`, callback_data: `chq:${x.id}` }]);
  await send(chat, "📣 <b>Kimni chaqiramiz?</b>", { reply_markup: { inline_keyboard: rows } });
}
const CHQ_MATN = ["Kabinetga keling", "Zudlik bilan kabinetga keling", "Bo‘sh vaqtingizda kabinetga kiring"];
async function chaqiruvYubor(chat: number, kimni: number, matn: string) {
  const c = await rpc("ep_chaqiruv_yarat", { p_kim_chat: chat, p_kimni_id: kimni, p_matn: matn });
  if (!c?.ok) { await send(chat, c?.xato === "tg_yoq" ? `${esc(c.ism)} Telegramga ulanmagan.` : "Xatolik"); return; }
  await send(Number(c.kimni_chat), `📣 <b>${esc(c.kim_ism)}</b> sizni chaqirmoqda:\n\n<i>${esc(matn)}</i>`, {
    reply_markup: { inline_keyboard: [[
      { text: "✅ Kelyapman", callback_data: `chj:${c.id}:Kelyapman` },
      { text: "⏱ 5 daqiqa", callback_data: `chj:${c.id}:5 daqiqadan keyin` },
      { text: "📚 Darsdaman", callback_data: `chj:${c.id}:Darsdaman, keyin kiraman` }]] } });
  await send(chat, `Yuborildi → <b>${esc(c.kimni_ism)}</b>. Javobini kutamiz.`);
}
async function arizalar(chat: number) {
  const d = await rpc("ep_teach_arizalar", { p_chat_id: chat });
  const r: any[] = d?.royxat ?? [];
  if (!r.length) { await send(chat, "Yangi ariza yo‘q ✅"); return; }
  for (const a of r) {
    await send(chat, `🆕 <b>${esc(a.ism)}</b>\n${esc(a.tel ?? "")}\n${a.vaqt ?? ""}`, { reply_markup: { inline_keyboard: [[
      { text: "✅ Tasdiqlash", callback_data: `ariza:${a.id}:1` }, { text: "❌ Rad etish", callback_data: `ariza:${a.id}:0` }]] } });
  }
}



// ---------- barcha o'qituvchilardan davomat so'rash ----------
async function davomatSoraYubor(quruq: boolean): Promise<{ yuborildi: number; jami: number }> {
  const h = await rpc("ep_teach_hozir", {});
  const oqit: any[] = ((h?.royxat ?? []) as any[]).filter((x: any) => x.tg);
  const sinflar: any[] = (await rpc("ep_sinflar_qisqa", {})) ?? [];
  const rows: any[] = [];
  for (let i = 0; i < sinflar.length; i += 4) rows.push(sinflar.slice(i, i + 4).map((x: any) => ({ text: x.nom, callback_data: `dv_sinf:${x.id}` })));
  let n = 0;
  for (const t of oqit) {
    const od = await rpc("ep_odam_chat", { p_id: t.id });
    if (!od?.chat_id) continue;
    if (!quruq) await send(Number(od.chat_id), "🕘 <b>Hozir qaysi sinfda darsdasiz?</b>\nSinfni tanlang — o‘quvchilar davomatini belgilaymiz.", { reply_markup: { inline_keyboard: rows } });
    n++;
  }
  return { yuborildi: n, jami: oqit.length };
}

// ---------- botdan davomat ----------
const DB_ICON: Record<string, string> = { keldi: "🟢", kelmadi: "🔴" };
function davKb(sinf: number, royxat: any[], belgi: Record<string, string>) {
  const rows = royxat.map((o: any) => [
    { text: `${DB_ICON[belgi[o.id]] ?? "⚪"} ${o.ism}`, callback_data: `dv_n:${sinf}:${o.id}` },
    { text: "✓", callback_data: `dv_k:${sinf}:${o.id}` },
    { text: "✗", callback_data: `dv_y:${sinf}:${o.id}` }]);
  rows.push([{ text: "✅ Hammasi keldi", callback_data: `dv_all:${sinf}` }]);
  rows.push([{ text: "📤 Davomatni yuborish", callback_data: `dv_send:${sinf}` }, { text: "✖ Bekor", callback_data: "dv_cancel" }]);
  return { inline_keyboard: rows };
}
async function davBoshla(chat: number, sinf: number, message_id?: number) {
  const d = await rpc("ep_dav_bot_royxat", { p_chat_id: chat, p_sinf_id: sinf });
  if (!d?.ok) { await send(chat, "Ruxsat yo‘q yoki sinf topilmadi."); return; }
  const belgi: Record<string, string> = {};
  (d.royxat ?? []).forEach((o: any) => { if (o.holat) belgi[o.id] = o.holat === "kech" ? "keldi" : o.holat; });
  await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: "davomat", p_malumot: { sinf, belgi, royxat: d.royxat } });
  const t = `📋 <b>${esc(d.sinf)} davomati</b> · ${d.kun}\nHar bir o‘quvchi uchun ✓ (keldi) yoki ✗ (kelmadi) bosing.`;
  if (message_id) await tg("editMessageText", { chat_id: chat, message_id, text: t, parse_mode: "HTML", reply_markup: davKb(sinf, d.royxat, belgi) });
  else await send(chat, t, { reply_markup: davKb(sinf, d.royxat, belgi) });
}
async function sinfSora(chat: number, sabab: string, cb: string) {
  const sinflar: any[] = (await rpc("ep_sinflar_qisqa", {})) ?? [];
  const rows: any[] = []; for (let i = 0; i < sinflar.length; i += 4) rows.push(sinflar.slice(i, i + 4).map((s: any) => ({ text: s.nom, callback_data: `${cb}:${s.id}` })));
  await send(chat, sabab, { reply_markup: { inline_keyboard: rows } });
}
async function davCallback(cq: any, k: string, a: string, b: string) {
  const chat = cq.message.chat.id as number, mid = cq.message.message_id;
  const ok = (text = "") => tg("answerCallbackQuery", { callback_query_id: cq.id, text });
  if (k === "dv_sinf") { await ok(); await tg("editMessageReplyMarkup", { chat_id: chat, message_id: mid, reply_markup: { inline_keyboard: [] } }); await davBoshla(chat, Number(a)); return; }
  if (k === "dv_cancel") { await ok("Bekor qilindi"); await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: null, p_malumot: null }); await tg("editMessageText", { chat_id: chat, message_id: mid, text: "Davomat bekor qilindi." }); return; }
  const st = await rpc("ep_tg_holat_ol", { p_chat_id: chat });
  if (st?.holat !== "davomat" || Number(st.malumot?.sinf) !== Number(a)) { await ok("Davomat qayta ochildi"); await davBoshla(chat, Number(a), mid); return; }
  const m = st.malumot; const belgi: Record<string, string> = m.belgi ?? {}; const royxat: any[] = m.royxat ?? [];
  if (k === "dv_k") belgi[b] = "keldi";
  if (k === "dv_y") belgi[b] = "kelmadi";
  if (k === "dv_n") belgi[b] = belgi[b] === "keldi" ? "kelmadi" : "keldi";
  if (k === "dv_all") royxat.forEach((o: any) => { belgi[o.id] = "keldi"; });
  if (k === "dv_send") {
    const yoq = royxat.filter((o: any) => !belgi[o.id]).length;
    if (yoq) { await ok(`${yoq} ta o‘quvchi belgilanmagan`); return; }
    const nk = royxat.filter((o: any) => belgi[o.id] === "keldi").length, nn = royxat.length - nk;
    await ok();
    await tg("editMessageText", { chat_id: chat, message_id: mid, parse_mode: "HTML",
      text: `⚠️ <b>Davomatni tasdiqlaysizmi?</b>\n\nKeldi: <b>${nk}</b>   Kelmadi: <b>${nn}</b>\n\nYolg‘on davomat aniqlansa, kamera yozuvi orqali tekshiriladi va chora ko‘riladi. Bu xabar ota-onalar va rahbariyatga sizning nomingizdan yuboriladi.`,
      reply_markup: { inline_keyboard: [[{ text: "✅ Ha, tasdiqlayman", callback_data: `dv_ok:${a}` }], [{ text: "◀️ O‘zgartirish", callback_data: `dv_back:${a}` }]] } });
    return;
  }
  if (k === "dv_back") { await ok(); await tg("editMessageText", { chat_id: chat, message_id: mid, parse_mode: "HTML", text: `📋 <b>Davomat</b> — davom eting`, reply_markup: davKb(Number(a), royxat, belgi) }); return; }
  if (k === "dv_ok") {
    const r = await rpc("ep_dav_bot_saqla", { p_chat_id: chat, p_sinf_id: Number(a), p_belgilar: belgi });
    if (!r?.ok) { await ok("Xatolik"); return; }
    await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: null, p_malumot: null });
    await ok("Saqlandi ✅");
    await tg("editMessageText", { chat_id: chat, message_id: mid, parse_mode: "HTML",
      text: `✅ <b>${esc(r.sinf)} davomati saqlandi</b>\nKeldi: ${r.keldi}, kelmadi: ${r.kelmadi}` + (r.kelmaganlar ? `\nKelmadi: <i>${esc(r.kelmaganlar)}</i>` : "") + `\n\nOta-onalarga xabar 3 daqiqada yetib boradi.` });
    const adm = await rpc("ep_adminlar_chat", {});
    for (const c of (Array.isArray(adm) ? adm : [])) {
      await send(Number(c), `📋 <b>${esc(r.sinf)}</b> davomati · o‘qituvchi <b>${esc(r.oqituvchi)}</b>\nKeldi: <b>${r.keldi}</b>   Kelmadi: <b>${r.kelmadi}</b>` + (r.kelmaganlar ? `\n<i>${esc(r.kelmaganlar)}</i>` : ""));
    }
    return;
  }
  await ok();
  await tg("editMessageReplyMarkup", { chat_id: chat, message_id: mid, reply_markup: davKb(Number(a), royxat, belgi) });
  await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: "davomat", p_malumot: { sinf: Number(a), belgi, royxat } });
}
// ---------- botdan xulosa ----------
async function xulosaSaqla(chat: number, m: any, xom: string) {
  const qatorlar = xom.split("\n").map((x) => x.trim()).filter(Boolean);
  let fan = "Dars", mavzu = "", matn = "";
  if (qatorlar.length >= 3) { fan = qatorlar[0]; mavzu = qatorlar[1]; matn = qatorlar.slice(2).join("\n"); }
  else if (qatorlar.length === 2) { mavzu = qatorlar[0]; matn = qatorlar[1]; }
  else { mavzu = "Dars xulosasi"; matn = qatorlar[0] ?? ""; }
  if (matn.length < 10) { await send(chat, "Xulosa juda qisqa — kamida 10 ta belgi yozing."); return; }
  if (mavzu.length < 2) mavzu = "Dars xulosasi";
  let ses: any = await rpc("ep_tg_sessiya", { p_chat_id: chat });
  if (!ses?.ok || !ses?.token) {
    const p = await rpc("ep_teach_pin", { p_chat_id: chat });
    if (!p?.ok) { await send(chat, T.royxatda_yoq); return; }
    ses = await rpc("ep_kirish", { p_pin: p.pin });
  }
  if (!ses?.token) { await send(chat, T.royxatda_yoq); return; }
  const bugun = new Date(Date.now() + 5 * 3600 * 1000).toISOString().slice(0, 10);
  const r = await rpc("ep_oq_xulosa_saqla", { p_token: ses.token, p_sana: bugun, p_raqam: Number(m.raqam) || 1,
    p_sinf_id: Number(m.sinf), p_fan: fan, p_mavzu: mavzu, p_matn: matn, p_belgilar: [] });
  await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: null, p_malumot: null });
  if (!r || r.ok === false) { await send(chat, `Saqlanmadi: <code>${esc(r?.xato ?? r?.message ?? "server")}</code>\nQaytadan urinib ko‘ring yoki kabinetdan yozing.`, { reply_markup: KB_TEACH }); return; }
  await send(chat, `✅ Xulosa saqlandi · ${esc(m.sinf_nom ?? "")} · ${esc(fan)} · ${Number(m.raqam) || 1}-dars\n<b>${esc(mavzu)}</b>\n\nOta-onalarga 2 daqiqada yetib boradi.`, { reply_markup: KB_TEACH });
}
// ---------- admin: ota-onalar ----------
async function otaRoyxat(chat: number, qaysi: "bor" | "yoq") {
  const d = await rpc("ep_ota_bot_royxat", { p_chat_id: chat });
  if (!d?.ok) { await send(chat, "Ruxsat yo‘q"); return; }
  const list: string[] = (d[qaysi] ?? []) as string[];
  const sarl = qaysi === "bor" ? `✅ <b>Botga ulangan ota-onalar</b> (${list.length})` : `❌ <b>Botga ulanmagan</b> (${list.length}) — telefon bilan`;
  if (!list.length) { await send(chat, sarl + "\n—"); return; }
  for (let i = 0; i < list.length; i += 40) await send(chat, (i === 0 ? sarl + "\n\n" : "") + list.slice(i, i + 40).map((x, j) => `${i + j + 1}. ${esc(x)}`).join("\n"));
}


// ---------- admin: o'quvchilar ro'yxati ----------
const JAVOB_MATN = "\n\n⚠️ <b>Diqqat:</b> bu o‘zgarish jurnalga sizning nomingiz bilan yoziladi. Siz uning to‘g‘riligi uchun javobgarsiz.";
async function oqRoyxat(chat: number, sinf: number, message_id?: number) {
  const d = await rpc("ep_oq_tg_royxat", { p_chat_id: chat, p_sinf_id: sinf });
  if (!d?.ok) { await send(chat, "Ruxsat yo‘q"); return; }
  const rows: any[] = (d.royxat ?? []).map((o: any) => [
    { text: o.ism, callback_data: `oq_i:${sinf}:${o.id}` },
    { text: "✏️", callback_data: `oq_ed:${sinf}:${o.id}` },
    { text: "🗑", callback_data: `oq_del:${sinf}:${o.id}` }]);
  rows.push([{ text: "➕ O‘quvchi qo‘shish", callback_data: `oq_add:${sinf}` }, { text: "◀️ Sinflar", callback_data: "oq_sinflar" }]);
  const t = `🎒 <b>${esc(d.sinf)}</b> · ${(d.royxat ?? []).length} ta o‘quvchi\n✏️ ismni o‘zgartirish · 🗑 ro‘yxatdan chiqarish`;
  if (message_id) await tg("editMessageText", { chat_id: chat, message_id, text: t, parse_mode: "HTML", reply_markup: { inline_keyboard: rows } });
  else await send(chat, t, { reply_markup: { inline_keyboard: rows } });
}
async function oqCallback(cq: any, k: string, a: string, b: string) {
  const chat = cq.message.chat.id as number, mid = cq.message.message_id;
  const ok = (text = "") => tg("answerCallbackQuery", { callback_query_id: cq.id, text });
  if (k === "oq_sinflar") { await ok(); await tg("editMessageReplyMarkup", { chat_id: chat, message_id: mid, reply_markup: { inline_keyboard: [] } }); await sinfSora(chat, "🎒 Qaysi sinf?", "oq_sinf"); return; }
  if (k === "oq_sinf") { await ok(); await tg("editMessageReplyMarkup", { chat_id: chat, message_id: mid, reply_markup: { inline_keyboard: [] } }); await oqRoyxat(chat, Number(a)); return; }
  if (k === "oq_i") { await ok("✏️ — ism, 🗑 — chiqarish"); return; }
  if (k === "oq_ed") {
    await ok();
    const nom = (cq.message.reply_markup?.inline_keyboard ?? []).flat().find((x: any) => x.callback_data === `oq_i:${a}:${b}`)?.text ?? "";
    await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: "oq_ism", p_malumot: { sinf: Number(a), id: Number(b), eski: nom } });
    await send(chat, `✏️ <b>${esc(nom)}</b> uchun yangi ism va familiyani yozing:`); return;
  }
  if (k === "oq_del") {
    await ok();
    const nom = (cq.message.reply_markup?.inline_keyboard ?? []).flat().find((x: any) => x.callback_data === `oq_i:${a}:${b}`)?.text ?? "";
    await send(chat, `🗑 <b>${esc(nom)}</b> ro‘yxatdan chiqarilsinmi?\nU davomat, obzvon va ota-ona xabarlaridan yo‘qoladi.` + JAVOB_MATN,
      { reply_markup: { inline_keyboard: [[{ text: "✅ Tasdiqlayman, javobgarman", callback_data: `oq_del_ok:${a}:${b}` }], [{ text: "✖ Bekor", callback_data: "oq_bekor" }]] } });
    return;
  }
  if (k === "oq_del_ok") {
    const r = await rpc("ep_oq_tg_ochir", { p_chat_id: chat, p_id: Number(b) });
    await ok(r?.ok ? "Chiqarildi" : "Xatolik");
    await tg("editMessageText", { chat_id: chat, message_id: mid, parse_mode: "HTML", text: r?.ok ? `🗑 <b>${esc(r.ism)}</b> (${esc(r.sinf)}) ro‘yxatdan chiqarildi. Jurnalga yozildi.` : "Xatolik" });
    if (r?.ok) await oqRoyxat(chat, Number(a));
    return;
  }
  if (k === "oq_add") {
    await ok();
    await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: "oq_qosh", p_malumot: { sinf: Number(a) } });
    await send(chat, "➕ Yangi o‘quvchining <b>ism va familiyasini</b> yozing:"); return;
  }
  if (k === "oq_bekor") { await ok("Bekor"); await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: null, p_malumot: null }); await tg("editMessageText", { chat_id: chat, message_id: mid, text: "Bekor qilindi." }); return; }
  if (k === "oq_ok") {
    const st = await rpc("ep_tg_holat_ol", { p_chat_id: chat }); const m = st?.malumot ?? {};
    let r: any = null, t = "Xatolik";
    if (st?.holat === "oq_ism_tasdiq") { r = await rpc("ep_oq_tg_ism", { p_chat_id: chat, p_id: Number(m.id), p_ism: m.yangi }); if (r?.ok) t = `✏️ <b>${esc(r.eski)}</b> → <b>${esc(r.yangi)}</b>. Jurnalga yozildi.`; }
    if (st?.holat === "oq_qosh_tasdiq") { r = await rpc("ep_oq_tg_qosh", { p_chat_id: chat, p_sinf_id: Number(m.sinf), p_ism: m.yangi }); if (r?.ok) t = `➕ <b>${esc(r.ism)}</b> ${esc(r.sinf)} sinfiga qo‘shildi. Jurnalga yozildi.`; else if (r?.xato === "bor") t = "Bunday o‘quvchi bu sinfda allaqachon bor."; }
    await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: null, p_malumot: null });
    await ok(r?.ok ? "Bajarildi" : "Xatolik");
    await tg("editMessageText", { chat_id: chat, message_id: mid, parse_mode: "HTML", text: t });
    if (r?.ok && m.sinf) await oqRoyxat(chat, Number(m.sinf));
    return;
  }
  await ok();
}


// ---------- talonlar (akademiya reyestri: hujjat_reyestr) ----------
const HJ = SAYT + "hujjat.html";
const HJ_NOM: Record<string, string> = { kelish: "Kelish taloni", ketish: "Ketish taloni", chb: "Buyruq — chiqarish", qb: "Buyruq — qabul" };
const HJ_SER: Record<string, string> = { kelish: "T", ketish: "KT", chb: "OQ", qb: "OQ" };
function oquvYili(): string { const d = new Date(Date.now() + 5 * 3600 * 1000); const y = d.getUTCFullYear(); return d.getUTCMonth() >= 7 ? `${y}-${y + 1}` : `${y - 1}-${y}`; }
async function talonMenyu(chat: number) {
  const o = await rpc("hujjat_oxirgi", { p_oquv: oquvYili() });
  const L = o ?? {};
  await send(chat, `🎫 <b>Talonlar va buyruqlar</b> · ${oquvYili()}\nOxirgi raqamlar: <b>${L.T ?? 0}</b>/T · <b>${L.KT ?? 0}</b>/KT · <b>${L.OQ ?? 0}</b>/O‘Q\n\nYangi hujjat — akademiyadagi bilan bir xil blank, reyestrga yoziladi va shu chatga PNG bo‘lib keladi.`, {
    reply_markup: { inline_keyboard: [
      [{ text: "📥 Kelish taloni", web_app: { url: HJ + "?tur=kelish" } }, { text: "📤 Ketish taloni", web_app: { url: HJ + "?tur=ketish" } }],
      [{ text: "📕 Buyruq — chiqarish", web_app: { url: HJ + "?tur=chb" } }, { text: "📗 Buyruq — qabul", web_app: { url: HJ + "?tur=qb" } }],
      [{ text: "🗂 Reyestr: kelish", callback_data: "hj_r:kelish" }, { text: "🗂 ketish", callback_data: "hj_r:ketish" }],
      [{ text: "🗂 chiqarish buyruqlari", callback_data: "hj_r:chb" }, { text: "🗂 qabul", callback_data: "hj_r:qb" }]] } });
}
async function hujjatReyestr(chat: number, turi: string, sahifa = 0, message_id?: number) {
  const hamma: any[] = (await rpc("hujjat_royxat_turi", { p_oquv: oquvYili(), p_turi: turi, p_bekor: false, p_limit: 500 })) ?? [];
  if (!Array.isArray(hamma) || !hamma.length) { await send(chat, `${HJ_NOM[turi] ?? turi}: hujjat yo‘q.`); return; }
  const H = 20, jami = hamma.length, bosh = sahifa * H, r = hamma.slice(bosh, bosh + H);
  const t = r.map((x: any) => `<b>№${x.raqam}${x.seriya ?? HJ_SER[turi]}</b> ${esc(x.fio)}` + (x.sinf ? ` (${esc(x.sinf)})` : "") + ` · ${esc(x.sana ?? "")}` + (x.fayl_bor ? "" : " · <i>fayl yo‘q</i>")).join("\n");
  const rows: any[] = [];
  const fayl = r.filter((x: any) => x.fayl_bor);
  for (let k = 0; k < fayl.length; k += 2) rows.push(fayl.slice(k, k + 2).map((x: any) => ({ text: `📎 №${x.raqam} ${String(x.fio).split(" ")[0]}`, callback_data: `hj_p:${x.id}` })));
  const nav: any[] = [];
  if (sahifa > 0) nav.push({ text: "◀️ Oldingi", callback_data: `hj_r:${turi}:${sahifa - 1}` });
  if (bosh + H < jami) nav.push({ text: "Keyingi ▶️", callback_data: `hj_r:${turi}:${sahifa + 1}` });
  if (nav.length) rows.push(nav);
  rows.push([{ text: "➕ Yangi " + (HJ_NOM[turi] ?? ""), web_app: { url: HJ + "?tur=" + turi } }]);
  const text = `🗂 <b>${HJ_NOM[turi] ?? turi}</b> · ${oquvYili()} · jami <b>${jami}</b> · ${bosh + 1}–${Math.min(bosh + H, jami)}\n\n${t}`;
  if (message_id) await tg("editMessageText", { chat_id: chat, message_id, text, parse_mode: "HTML", reply_markup: { inline_keyboard: rows } });
  else await send(chat, text, { reply_markup: { inline_keyboard: rows } });
}
async function hujjatPngYubor(chat: number, dataUrl: string, nom: string, izoh: string) {
  const b64 = dataUrl.split(",")[1] ?? ""; if (!b64) return false;
  const bin = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  const pdf = dataUrl.indexOf("application/pdf") >= 0;
  const fd = new FormData();
  fd.append("chat_id", String(chat)); fd.append("caption", izoh); fd.append("parse_mode", "HTML");
  fd.append("document", new Blob([bin], { type: pdf ? "application/pdf" : "image/png" }), nom + (pdf ? ".pdf" : ".png"));
  const r = await fetch(`https://api.telegram.org/bot${TEACH}/sendDocument`, { method: "POST", body: fd }).then((x) => x.json()).catch(() => null);
  return !!r?.ok;
}
async function talonCallback(cq: any, k: string, a: string, b?: string) {
  const chat = cq.message.chat.id as number;
  const ok = (text = "") => tg("answerCallbackQuery", { callback_query_id: cq.id, text });
  if (k === "hj_r") { await ok(); await hujjatReyestr(chat, a, Number(b ?? 0) || 0, Number(b ?? 0) > 0 || cq.message?.text?.includes("jami") ? cq.message.message_id : undefined); return; }
  if (k === "hj_p") {
    await ok("Arxivdan olinmoqda…");
    const x: any = ((await rpc("hujjat_bitta", { p_id: Number(a) })) ?? [])[0];
    const png = await rpc("hujjat_png_ol", { p_id: Number(a) });
    if (!x || !png || typeof png !== "string") { await send(chat, "Fayl topilmadi."); return; }
    const base = ({ kelish: "KELISH_TALON", ketish: "KETISH_TALON", chb: "BUYRUQ_CHIQARISH", qb: "BUYRUQ_QABUL" } as any)[x.turi] ?? "HUJJAT";
    const okk = await hujjatPngYubor(chat, png, `${base}_${x.raqam}${x.seriya ?? ""}`, `${HJ_NOM[x.turi] ?? x.turi} №${x.raqam}${x.seriya ?? ""} · ${esc(x.fio)}`);
    if (!okk) await send(chat, "Yuborib bo‘lmadi.");
    return;
  }
  await ok();
}


// ---------- kim xulosa yozgan ----------
async function xulosaHisobot(chat: number, kun: string | null = null) {
  const d = await rpc("ep_xulosa_hisobot_tg", { p_chat_id: chat, p_kun: kun });
  if (!d?.ok) { await send(chat, "Ruxsat yo‘q"); return; }
  const r: any[] = d.royxat ?? [];
  const yozgan = r.filter((x: any) => Number(x.soni) > 0), yoq = r.filter((x: any) => !Number(x.soni));
  let t = `📝 <b>Dars xulosalari</b> · ${d.kun}\nYozgan: <b>${d.yozgan}</b> / ${d.jami_oqituvchi} o‘qituvchi · darslar: <b>${d.darslar}</b>\n`;
  if (yozgan.length) {
    t += `\n<b>✅ Yozganlar</b>\n`;
    yozgan.forEach((x: any) => { t += `<b>${esc(x.ism)}</b> — ${x.soni} ta` + (x.oxirgi ? ` · ${x.oxirgi}` : "") + "\n" + (x.darslar ? `<i>${esc(x.darslar)}</i>\n` : ""); });
  }
  if (yoq.length) {
    t += `\n<b>❌ Yozmaganlar (${yoq.length})</b>\n` + yoq.map((x: any) => `• ${esc(x.ism)}` + (x.tg ? "" : " <i>(TG yo‘q)</i>")).join("\n");
  }
  const rows = [[{ text: "🔄 Yangilash", callback_data: "xh:bugun" }, { text: "◀️ Kecha", callback_data: "xh:kecha" }]];
  for (let i = 0; i < t.length; i += 3800) {
    const oxirgi = i + 3800 >= t.length;
    await send(chat, t.slice(i, i + 3800), oxirgi ? { reply_markup: { inline_keyboard: rows } } : {});
  }
}


// ---------- o'qituvchilar ro'yxati ----------
async function oqitRoyxat(chat: number) {
  const d = await rpc("ep_oqit_royxat_tg", { p_chat_id: chat });
  if (!d?.ok) { await send(chat, "Ruxsat yo‘q"); return; }
  const r: any[] = d.royxat ?? [];
  const t = r.map((x: any, i: number) => `${i + 1}. <b>${esc(x.ism)}</b>` + (x.tg ? " ✅" : " <i>TG yo‘q</i>") +
    (x.tel ? ` · ${esc(x.tel)}` : "") + ` · PIN <code>${esc(x.pin)}</code>` +
    (Number(x.xulosa) ? ` · bugun ${x.xulosa} xulosa` : "")).join("\n");
  const rows: any[] = [[{ text: "➕ O‘qituvchi qo‘shish", callback_data: "oqt_add" }]];
  for (let k = 0; k < r.length; k += 2) rows.push(r.slice(k, k + 2).map((x: any) => ({ text: `🗑 ${String(x.ism).split(" ")[0]}`, callback_data: `oqt_del:${x.id}` })));
  await send(chat, `👩‍🏫 <b>O‘qituvchilar</b> · ${d.jami} ta · Telegramda ${d.tg}\n\n${t || "—"}`, { reply_markup: { inline_keyboard: rows.slice(0, 20) } });
}
async function oqitCallback(cq: any, k: string, a: string) {
  const chat = cq.message.chat.id as number, mid = cq.message.message_id;
  const ok = (text = "") => tg("answerCallbackQuery", { callback_query_id: cq.id, text });
  if (k === "oqt_add") {
    await ok();
    await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: "oqit_ism", p_malumot: null });
    await send(chat, "➕ Yangi o‘qituvchining <b>ism va familiyasini</b> yozing:");
    return;
  }
  if (k === "oqt_del") {
    await ok();
    const d = await rpc("ep_oqit_royxat_tg", { p_chat_id: chat });
    const x = ((d?.royxat ?? []) as any[]).find((y: any) => Number(y.id) === Number(a));
    if (!x) { await send(chat, "Topilmadi"); return; }
    await send(chat, `🗑 <b>${esc(x.ism)}</b> ishdan chiqarilsinmi?\nU botdan, davomatdan va chaqiruvlardan yo‘qoladi, PIN ishlamay qoladi.` + JAVOB_MATN,
      { reply_markup: { inline_keyboard: [[{ text: "✅ Tasdiqlayman, javobgarman", callback_data: `oqt_del_ok:${a}` }], [{ text: "✖ Bekor", callback_data: "oq_bekor" }]] } });
    return;
  }
  if (k === "oqt_del_ok") {
    const r = await rpc("ep_oqit_ochir_tg", { p_chat_id: chat, p_id: Number(a) });
    await ok(r?.ok ? "Chiqarildi" : "Xatolik");
    await tg("editMessageText", { chat_id: chat, message_id: mid, parse_mode: "HTML",
      text: r?.ok ? `🗑 <b>${esc(r.ism)}</b> ishdan chiqarildi. Jurnalga yozildi.` : "Xatolik" });
    if (r?.ok) await oqitRoyxat(chat);
    return;
  }
  if (k === "oqt_ok") {
    const st = await rpc("ep_tg_holat_ol", { p_chat_id: chat }); const m = st?.malumot ?? {};
    const r = await rpc("ep_oqit_qosh_tg", { p_chat_id: chat, p_ism: m.ism, p_tel: m.tel ?? null });
    await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: null, p_malumot: null });
    await ok(r?.ok ? "Qo‘shildi" : "Xatolik");
    await tg("editMessageText", { chat_id: chat, message_id: mid, parse_mode: "HTML",
      text: r?.ok ? `➕ <b>${esc(r.ism)}</b> qo‘shildi.\nPIN: <code>${esc(r.pin)}</code>\n\nO‘qituvchi botda <b>/start</b> bosib ro‘yxatdan o‘tsin — shunda unga xabarlar boradi.`
        : (r?.xato === "bor" ? "Bunday o‘qituvchi allaqachon bor." : "Xatolik") });
    if (r?.ok) await oqitRoyxat(chat);
    return;
  }
  await ok();
}

// ---------- xabarlar ----------
async function xabar(msg: any) {
  const chat = msg.chat?.id as number; if (!chat) return;
  const matn = (msg.text ?? "").trim();
  const rol = await rpc("ep_tg_rol", { p_chat_id: chat });
  const isAdmin = rol?.ok && rol.rol === "admin";
  const isTeach = rol?.ok && rol.rol === "oqituvchi";

  if (msg.location) {
    const { latitude, longitude, live_period } = msg.location;
    const nuq = await rpc("ep_maktab_nuqta", { p_chat_id: chat, p_lat: latitude, p_lon: longitude });
    if (nuq?.ok) { await send(chat, T.maktab_ok(latitude, longitude, nuq.radius), { reply_markup: isAdmin ? KB_ADMIN : KB_TEACH }); return; }
    const d = await rpc("ep_teach_lok_saqla", { p_chat_id: chat, p_lat: latitude, p_lon: longitude, p_live_sek: live_period ?? 0 });
    if (!d?.ok) { if (!msg.edit_date) await send(chat, T.royxatda_yoq); return; }
    if (msg.edit_date) return; // jonli yangilanish — jim
    await send(chat, d.maktab ? (d.ichkarida ? `Joylashuv qabul qilindi ✅ Maktabgacha ${d.masofa} m.` : `Joylashuv qabul qilindi. Maktabdan ${d.masofa} m uzoqda.`) : "Joylashuv qabul qilindi ✅", { reply_markup: KB_TEACH });
    return;
  }

  const st = await rpc("ep_tg_holat_ol", { p_chat_id: chat });
  // --- holatli javoblar ---
  if (st?.holat === "admin_pin" && !matn.startsWith("/")) {
    await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: null, p_malumot: null });
    const a = await rpc("ep_tg_admin_ulash", { p_chat_id: chat, p_pin: matn });
    if (a?.ok) await adminMenyu(chat, a.ism); else await send(chat, T.admin_xato);
    return;
  }
  if (st?.holat === "oqit_ism" && !matn.startsWith("/")) {
    const ism = matn.replace(/\s+/g, " ").trim();
    if (ism.length < 5 || ism.indexOf(" ") < 0) { await send(chat, "Ism va familiyani to‘liq yozing."); return; }
    await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: "oqit_tel", p_malumot: { ism } });
    await send(chat, `<b>${esc(ism)}</b> — telefon raqamini yozing (yoki <b>yo‘q</b>):`);
    return;
  }
  if (st?.holat === "oqit_tel" && !matn.startsWith("/")) {
    const m = st.malumot ?? {}; const tel = /^(yo‘q|yoq|-)$/i.test(matn.trim()) ? null : matn.trim();
    await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: "oqit_tasdiq", p_malumot: { ...m, tel } });
    await send(chat, `➕ Yangi o‘qituvchi: <b>${esc(m.ism)}</b>` + (tel ? `\n${esc(tel)}` : "") + JAVOB_MATN,
      { reply_markup: { inline_keyboard: [[{ text: "✅ Tasdiqlayman, javobgarman", callback_data: "oqt_ok" }], [{ text: "✖ Bekor", callback_data: "oq_bekor" }]] } });
    return;
  }
  if ((st?.holat === "oq_ism" || st?.holat === "oq_qosh") && !matn.startsWith("/")) {
    const m = st.malumot ?? {}; const yangi = matn.replace(/\s+/g, " ").trim();
    if (yangi.length < 4) { await send(chat, "Ism juda qisqa. Qaytadan yozing:"); return; }
    const tasdiq = st.holat === "oq_ism" ? "oq_ism_tasdiq" : "oq_qosh_tasdiq";
    await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: tasdiq, p_malumot: { ...m, yangi } });
    const t = st.holat === "oq_ism" ? `✏️ <b>${esc(m.eski)}</b> → <b>${esc(yangi)}</b>` : `➕ Yangi o‘quvchi: <b>${esc(yangi)}</b>`;
    await send(chat, t + JAVOB_MATN, { reply_markup: { inline_keyboard: [[{ text: "✅ Tasdiqlayman, javobgarman", callback_data: "oq_ok" }], [{ text: "✖ Bekor", callback_data: "oq_bekor" }]] } });
    return;
  }
  if (st?.holat === "xulosa_matn" && !matn.startsWith("/")) { await xulosaSaqla(chat, st.malumot ?? {}, matn); return; }
  if (st?.holat === "ommaviy" && !matn.startsWith("/")) {
    await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: "ommaviy_tasdiq", p_malumot: { matn } });
    await send(chat, `📢 Barcha ota-onalarga yuborilsinmi?

<i>${esc(matn)}</i>`, { reply_markup: { inline_keyboard: [[{ text: "✅ Yuborish", callback_data: "omm_ok" }, { text: "✖ Bekor", callback_data: "omm_no" }]] } });
    return;
  }
  if (st?.holat === "chaqiruv_matn" && !matn.startsWith("/")) {
    await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: null, p_malumot: null });
    await chaqiruvYubor(chat, Number(st.malumot?.kimni), matn); return;
  }

  // --- buyruqlar ---
  if (matn === "/admin") { await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: "admin_pin", p_malumot: null }); await send(chat, T.admin_pin); return; }
  if (matn === "/start" || matn === "/boshla") {
    if (isAdmin) { await adminMenyu(chat, rol.ism); return; }
    if (isTeach) { await send(chat, `Salom, <b>${esc(rol.ism)}</b>!`, { reply_markup: KB_TEACH }); return; }
    await rpc("ep_teach_boshla", { p_chat_id: chat }); await send(chat, T.salom); return;
  }
  if (matn === "/maktab") {
    const k = await rpc("ep_maktab_kutish", { p_chat_id: chat });
    if (!k?.ok) { await send(chat, "Bu buyruq faqat rahbariyat uchun."); return; }
    await send(chat, "Maktab hovlisida turib joylashuvingizni yuboring — u markaz bo‘ladi. 5 daqiqa vaqt bor.", { reply_markup: KB_LOK }); return;
  }
  if (matn === "/pin" || /^\S*\s*pin$/i.test(matn)) {
    const p = await rpc("ep_teach_pin", { p_chat_id: chat });
    await send(chat, p?.ok ? `PIN: <b>${p.pin}</b>\n${SAYT}oqituvchi-kabinet.html` : T.royxatda_yoq); return;
  }
  if (matn === "/holat" || /holatim/i.test(matn)) {
    const h = await rpc("ep_teach_holat", { p_chat_id: chat });
    if (!h?.ok) { await send(chat, T.royxatda_yoq); return; }
    await send(chat, `Bugun: <b>${h.ichkarida}/${h.jami}</b> belgi maktab ichida.` + (h.oxirgi ? `\nOxirgi joylashuv: ${h.oxirgi}` : "\nBugun joylashuv kelmadi.")); return;
  }
  if (/davomat belgilash/i.test(matn)) { if (!isTeach && !isAdmin) { await send(chat, T.royxatda_yoq); return; } await sinfSora(chat, "Qaysi sinf davomatini belgilaysiz?", "dv_sinf"); return; }
  if (/xulosa yozish/i.test(matn)) { if (!isTeach) { await send(chat, T.royxatda_yoq); return; } await sinfSora(chat, "Qaysi sinf uchun xulosa yozasiz?", "xl_sinf"); return; }
  if (/kabinet$/i.test(matn)) { await send(chat, "Kabinet ilova sifatida ochiladi — PIN kerak emas.", { reply_markup: KB_APP() }); return; }

  if (isAdmin) {
    if (/kim maktabda/i.test(matn)) { await send(chat, await kimMaktabda()); return; }
    if (/davomat hisoboti/i.test(matn) || matn === "📋 Davomat") { await send(chat, await davomatMatn(false), { reply_markup: { inline_keyboard: [[{ text: "👥 Kelmaganlar ismlari", callback_data: "kelmaganlar" }]] } }); return; }
    if (/chaqirish/i.test(matn)) { await chaqirishRoyxat(chat); return; }
    if (/arizalar/i.test(matn)) { await arizalar(chat); return; }
    if (/o‘qituvchilar|o'qituvchilar|oqituvchilar/i.test(matn)) { await oqitRoyxat(chat); return; }
    if (/xulosalar/i.test(matn)) { await xulosaHisobot(chat); return; }
    if (/talon/i.test(matn)) { await talonMenyu(chat); return; }
    if (/davomat so/i.test(matn)) {
      const h = await rpc("ep_teach_hozir", {});
      const n = ((h?.royxat ?? []) as any[]).filter((x: any) => x.tg).length;
      await send(chat, `📤 <b>Barcha o‘qituvchilardan davomat so‘raymizmi?</b>\n\n${n} ta o‘qituvchiga «Hozir qaysi sinfda darsdasiz?» xabari boradi va ular sinfni tanlab davomat belgilaydi.`,
        { reply_markup: { inline_keyboard: [[{ text: "✅ Ha, yuborilsin", callback_data: "dsora_ok" }], [{ text: "✖ Bekor", callback_data: "dsora_no" }]] } });
      return;
    }
    if (/o‘quvchilar|o'quvchilar|oquvchilar/i.test(matn)) { await sinfSora(chat, "🎒 Qaysi sinf?", "oq_sinf"); return; }
    if (/ota-onalar/i.test(matn)) { await send(chat, "Qaysi ro‘yxat?", { reply_markup: { inline_keyboard: [[{ text: "✅ Botda", callback_data: "ota_bor" }, { text: "❌ Botda emas", callback_data: "ota_yoq" }]] } }); return; }
    if (/^\S*\s*xabar$/i.test(matn)) { await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: "ommaviy", p_malumot: null }); await send(chat, "Barcha ota-onalarga yuboriladigan xabar matnini yozing:"); return; }
    await send(chat, "Menyudan tanlang 👇", { reply_markup: KB_ADMIN }); return;
  }
  if (matn.startsWith("/")) { await send(chat, "/holat · /pin · /admin"); return; }

  // --- ro'yxatdan o'tish ---
  const d = await rpc("ep_teach_matn", { p_chat_id: chat, p_matn: matn });
  switch (d?.javob) {
    case "allaqachon": await send(chat, `Siz allaqachon ro‘yxatdasiz.\nPIN: <b>${d.pin}</b>`, { reply_markup: KB_TEACH }); break;
    case "ism_xato": await send(chat, T.ism_xato); break;
    case "tel_sora": await send(chat, T.tel); break;
    case "tel_xato": await send(chat, T.tel_xato); break;
    case "kutilmoqda": case "kutilmoqda_takror": await send(chat, T.kutilmoqda); break;
    default: await send(chat, T.salom);
  }
}

// ---------- tugma bosishlari ----------
async function callback(cq: any) {
  const chat = cq.message?.chat?.id as number; const data = String(cq.data ?? "");
  const ok = (text = "") => tg("answerCallbackQuery", { callback_query_id: cq.id, text });
  const [k, a, b] = data.split(":");
  if (k.startsWith("dv_")) { await davCallback(cq, k, a, b); return; }
  if (k.startsWith("oqt_")) { await oqitCallback(cq, k, a); return; }
  if (k.startsWith("oq_")) { await oqCallback(cq, k, a, b); return; }
  if (k.startsWith("hj_")) { await talonCallback(cq, k, a, b); return; }
  if (k === "xh") { await ok(); const kecha=new Date(Date.now()+5*3600*1000-(a==="kecha"?86400000:0)).toISOString().slice(0,10); await xulosaHisobot(chat, kecha); return; }
  if (k === "dsora_no") { await ok("Bekor"); await tg("editMessageText", { chat_id: chat, message_id: cq.message.message_id, text: "Bekor qilindi." }); return; }
  if (k === "dsora_ok") {
    if (!(await rpc("ep_tg_rol", { p_chat_id: chat }))?.ok) { await ok("Ruxsat yo‘q"); return; }
    await ok("Yuborilmoqda…");
    await tg("editMessageText", { chat_id: chat, message_id: cq.message.message_id, text: "📤 Yuborilmoqda…" });
    const r = await davomatSoraYubor(false);
    await tg("editMessageText", { chat_id: chat, message_id: cq.message.message_id, parse_mode: "HTML",
      text: `📤 <b>${r.yuborildi}</b> ta o‘qituvchiga davomat so‘rovi yuborildi.` });
    return;
  }
  if (k === "xl_sinf") {
    await ok();
    const sinflar: any[] = (await rpc("ep_sinflar_qisqa", {})) ?? [];
    const nom = (sinflar.find((x: any) => Number(x.id) === Number(a)) ?? {}).nom ?? "";
    await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: "xulosa_raqam", p_malumot: { sinf: Number(a), sinf_nom: nom } });
    const rows: any[] = []; for (let i = 1; i <= 8; i += 4) rows.push([1, 2, 3, 4].map((d) => ({ text: String(i + d - 1), callback_data: `xl_raqam:${i + d - 1}` })));
    await send(chat, `${esc(nom)} — nechanchi dars?`, { reply_markup: { inline_keyboard: rows } });
    return;
  }
  if (k === "xl_raqam") {
    await ok();
    const st = await rpc("ep_tg_holat_ol", { p_chat_id: chat });
    await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: "xulosa_matn", p_malumot: { ...(st?.malumot ?? {}), raqam: Number(a) } });
    await send(chat, "Endi <b>bitta xabarda</b> yozing:\n\n<code>Fan nomi\nMavzu\nQisqacha xulosa (kamida 10 belgi)</code>\n\nMasalan:\n<i>Matematika\nKasrlarni qo‘shish\nBugun kasrlarni qo‘shishni o‘rgandik, uy vazifasi 45-mashq.</i>");
    return;
  }
  if (k === "xl_menu") { await ok(); await sinfSora(chat, "Qaysi sinf uchun xulosa yozasiz?", "xl_sinf"); return; }
  if (k === "ota_bor" || k === "ota_yoq") { await ok(); await otaRoyxat(chat, k === "ota_bor" ? "bor" : "yoq"); return; }
  if (k === "omm_no") { await ok("Bekor"); await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: null, p_malumot: null }); await tg("editMessageText", { chat_id: chat, message_id: cq.message.message_id, text: "Bekor qilindi." }); return; }
  if (k === "omm_ok") {
    const st = await rpc("ep_tg_holat_ol", { p_chat_id: chat });
    const r = await rpc("ep_ota_ommaviy", { p_chat_id: chat, p_matn: st?.malumot?.matn ?? "" });
    await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: null, p_malumot: null });
    await ok(r?.ok ? "Yuborildi" : "Xatolik");
    await tg("editMessageText", { chat_id: chat, message_id: cq.message.message_id, text: r?.ok ? `📢 ${r.soni} ta ota-onaga navbatga qo‘yildi — 1 daqiqada yetib boradi.` : "Xatolik" });
    return;
  }
  if (k === "ariza") {
    const d = await rpc("ep_teach_tasdiq_tg", { p_chat_id: chat, p_ariza_id: Number(a), p_ok: b === "1" });
    if (!d?.ok) { await ok(d?.xato === "topilmadi" ? "Allaqachon hal qilingan" : "Ruxsat yo‘q"); return; }
    await ok(d.holat === "tasdiqlandi" ? "Tasdiqlandi ✅" : "Rad etildi");
    await tg("editMessageReplyMarkup", { chat_id: chat, message_id: cq.message.message_id, reply_markup: { inline_keyboard: [] } });
    await send(chat, (d.holat === "tasdiqlandi" ? "✅ " : "❌ ") + esc(d.ism) + (d.holat === "tasdiqlandi" ? " tasdiqlandi, PIN yuborildi." : " rad etildi."));
    await send(Number(d.chat_id), d.holat === "tasdiqlandi" ? T.tasdiq(d.pin) : T.rad, d.holat === "tasdiqlandi" ? { reply_markup: KB_TEACH } : {});
    return;
  }
  if (k === "chq") {
    await ok();
    const rows = CHQ_MATN.map((m, i) => [{ text: m, callback_data: `chqm:${a}:${i}` }]);
    rows.push([{ text: "✍️ O‘z matnim", callback_data: `chqm:${a}:x` }]);
    await send(chat, "Xabar matni:", { reply_markup: { inline_keyboard: rows } }); return;
  }
  if (k === "chqm") {
    await ok();
    if (b === "x") { await rpc("ep_tg_holat_qoy", { p_chat_id: chat, p_holat: "chaqiruv_matn", p_malumot: { kimni: Number(a) } }); await send(chat, "Xabar matnini yozing:"); return; }
    await chaqiruvYubor(chat, Number(a), CHQ_MATN[Number(b)] ?? CHQ_MATN[0]); return;
  }
  if (k === "chj") {
    const j = data.slice(data.indexOf(":", 4) + 1);
    const d = await rpc("ep_chaqiruv_javob", { p_id: Number(a), p_chat_id: chat, p_javob: j });
    await ok(d?.ok ? "Javob yuborildi" : "Xatolik");
    if (d?.ok) {
      await tg("editMessageReplyMarkup", { chat_id: chat, message_id: cq.message.message_id, reply_markup: { inline_keyboard: [] } });
      await send(chat, `Javobingiz yuborildi: <i>${esc(j)}</i>`);
      if (d.kim_chat) await send(Number(d.kim_chat), `💬 <b>${esc(d.kimni_ism)}</b>: ${esc(j)}`);
    }
    return;
  }
  if (k === "kelmaganlar") { await ok(); await send(chat, await davomatMatn(true)); return; }
  await ok();
}

// ---------- navbat: ikkala bot orqali yuborish ----------
async function navbatYubor(): Promise<{ teach: number; ota: number; xato: number }> {
  const n = { teach: 0, ota: 0, xato: 0 };
  for (const bot of ["teach", "ota"] as const) {
    const token = bot === "teach" ? TEACH : OTA; if (!token) continue;
    const list: any[] = (await rpc("ep_xabar_ol", { p_bot: bot, p_limit: 40 })) ?? [];
    for (const m of list) {
      const r = await send(Number(m.chat_id), m.matn, m.tugmalar ? { reply_markup: m.tugmalar } : {}, token);
      await rpc("ep_xabar_natija", { p_id: m.id, p_ok: !!r?.ok, p_xato: r?.ok ? null : JSON.stringify(r).slice(0, 200) });
      if (r?.ok) n[bot]++; else n.xato++;
    }
  }
  const kut: any[] = (await rpc("ep_chaqiruv_kutilayotgan", {})) ?? [];
  for (const c of kut) {
    if (c.kimni_chat) await send(Number(c.kimni_chat), `🔔 <b>Eslatma:</b> sizni chaqirishgan — <i>${esc(c.matn)}</i>. Javob bering.`);
    if (c.kim_chat) await send(Number(c.kim_chat), `⏳ <b>${esc(c.kimni_ism)}</b> 5 daqiqadan beri javob bermadi.`);
  }
  return n;
}

// ---------- WebApp initData tekshiruvi ----------
async function hmac(keyRaw: ArrayBuffer | Uint8Array, msg: string) {
  const key = await crypto.subtle.importKey("raw", keyRaw as ArrayBuffer, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(msg)));
}
async function initDataTekshir(initData: string, token: string): Promise<number | null> {
  try {
    const p = new URLSearchParams(initData); const hash = p.get("hash"); if (!hash) return null;
    p.delete("hash");
    const dcs = [...p.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${k}=${v}`).join("\n");
    const secret = await hmac(new TextEncoder().encode("WebAppData"), token);
    const sig = await hmac(secret, dcs);
    const hex = [...sig].map((x) => x.toString(16).padStart(2, "0")).join("");
    if (hex !== hash) return null;
    const auth = Number(p.get("auth_date") ?? 0); if (Date.now() / 1000 - auth > 86400) return null;
    const u = JSON.parse(p.get("user") ?? "{}"); return u?.id ? Number(u.id) : null;
  } catch { return null; }
}

Deno.serve(async (req) => {
  const url = new URL(req.url); const q = (k: string) => url.searchParams.get(k);
  const QURUQ = q("quruq") !== null;
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });

  if (q("setup") !== null || q("ulash") !== null) {
    let ruxsat = !!(q("setup") && CRON && q("setup") === CRON);
    if (!ruxsat && q("ulash") !== null) { const b = await req.json().catch(() => ({})); const a = await rpc("ep_admin_tekshir", { p_token: (b as any).token ?? "" }); ruxsat = !!a?.ok; }
    if (!ruxsat) return no();
    const r = await tg("setWebhook", { url: FN(), secret_token: CRON, allowed_updates: ["message", "edited_message", "callback_query"], drop_pending_updates: true });
    const me = await tg("getMe", {});
    return jsonc({ setWebhook: r, bot: me?.result?.username ?? null });
  }
  if (q("info") !== null) {
    const b = await req.json().catch(() => ({})); const a = await rpc("ep_admin_tekshir", { p_token: (b as any).token ?? "" }); if (!a?.ok) return no();
    const wi = await tg("getWebhookInfo", {}); const me = await tg("getMe", {});
    return jsonc({ webhook: wi?.result ?? wi, bot: me?.result?.username ?? null, cron_bor: !!CRON, token_bor: !!TEACH, ota_bor: !!OTA });
  }
  if (q("webapp") !== null) {
    const b = await req.json().catch(() => ({})) as any;
    const token = b.bot === "ota" ? OTA : TEACH;
    const uid = await initDataTekshir(String(b.initData ?? ""), token);
    if (!uid) return jsonc({ ok: false, xato: "initData" }, 401);
    let s: any = await rpc("ep_tg_sessiya", { p_chat_id: uid });
    if (!s?.ok || !s?.token) {
      const rol = await rpc("ep_tg_rol", { p_chat_id: uid });
      if (rol?.ok) {
        const pin = rol.rol === "oqituvchi" ? await rpc("ep_teach_pin", { p_chat_id: uid }) : null;
        if (pin?.ok) { const k = await rpc("ep_kirish", { p_pin: pin.pin }); if (k?.token) s = { ok: true, token: k.token, rol: k.rol, ism: rol.ism }; }
      }
    }
    return jsonc(s ?? { ok: false });
  }
  if (q("hujjat") !== null) {
    const b = await req.json().catch(() => ({})) as any;
    const uid = await initDataTekshir(String(b.initData ?? ""), TEACH);
    if (!uid) return jsonc({ ok: false, xato: "initData" }, 401);
    const rol = await rpc("ep_tg_rol", { p_chat_id: uid });
    if (!rol?.ok || rol.rol !== "admin") return jsonc({ ok: false, xato: "ruxsat" }, 403);
    const turi = String(b.turi ?? ""); const nom = `${({ kelish: "KELISH_TALON", ketish: "KETISH_TALON", chb: "BUYRUQ_CHIQARISH", qb: "BUYRUQ_QABUL" } as any)[turi] ?? "HUJJAT"}_${b.raqam ?? ""}${HJ_SER[turi] ?? ""}`;
    const izoh = `${HJ_NOM[turi] ?? "Hujjat"} №${b.raqam ?? ""}${HJ_SER[turi] ?? ""} · ${esc(b.fio ?? "")}\n<i>Berdi: ${esc(rol.ism)}</i>`;
    const ok1 = await hujjatPngYubor(uid, String(b.png ?? ""), nom, izoh);
    const adm = await rpc("ep_adminlar_chat", {}); let n = ok1 ? 1 : 0;
    for (const c of (Array.isArray(adm) ? adm : [])) { if (Number(c) !== uid) { if (await hujjatPngYubor(Number(c), String(b.png ?? ""), nom, izoh)) n++; } }
    return jsonc({ ok: ok1, yuborildi: n });
  }
  if (q("tekshir") !== null) { if (!(await cronOk(q("tekshir")))) return no(); return jsonc(await rpc("ep_teach_tekshir", {})); }
  if (q("eslatma") !== null) {
    if (!(await cronOk(q("eslatma")))) return no();
    const d = await rpc("ep_teach_eslatma", {}); let n = 0;
    for (const t of (d?.royxat ?? [])) { if (!QURUQ) await send(t.chat_id, T.eslatma, { reply_markup: KB_LOK }); n++; }
    return jsonc({ ok: true, yuborildi: n });
  }
  if (q("navbat") !== null) { if (!(await cronOk(q("navbat")))) return no(); return jsonc({ ok: true, ...(await navbatYubor()) }); }
  if (q("xulosa") !== null) {
    if (!(await cronOk(q("xulosa")))) return no();
    const t = await davomatMatn(true); let n = 0;
    const d = await rpc("ep_adminlar_chat", {});
    for (const c of (Array.isArray(d) ? d : [])) { if (!QURUQ) await send(Number(c), "🕙 <b>Kunlik hisobot</b>\n\n" + t); n++; }
    return jsonc({ ok: true, yuborildi: n });
  }
  if (q("brend") !== null) {
    const b = await req.json().catch(() => ({})) as any;
    const a = await rpc("ep_admin_tekshir", { p_token: b.token ?? "" });
    if (!a?.ok && !(CRON && q("brend") === CRON)) return no();
    const natija: any = {};

    const T_QISQA = "EduNova School — o‘qituvchilar va rahbariyat uchun rasmiy bot.";
    const T_UZUN =
      "EduNova School rasmiy boti.\n\n" +
      "O‘qituvchilar uchun: ro‘yxatdan o‘tish, shaxsiy PIN, kabinet, jonli joylashuv orqali davomat, rahbariyat chaqiruvlariga javob.\n\n" +
      "Rahbariyat uchun: kim maktabda ekanini ko‘rish, o‘quvchilar davomati, o‘qituvchini chaqirish, yangi arizalarni tasdiqlash.\n\n" +
      "Boshlash uchun /start bosing.";
    const O_QISQA = "EduNova School — ota-onalar uchun rasmiy bot.";
    const O_UZUN =
      "EduNova School rasmiy boti — ota-onalar uchun.\n\n" +
      "Farzandingiz maktabga kelgani haqida xabar, davomat, dars natijalari, to‘lov jadvali va shaxsiy kabinet PIN kodi.\n\n" +
      "Kabinetga kirish uchun shartnoma imzolanganda berilgan PIN kod ishlatiladi.";

    const T_CMD = [
      { command: "start", description: "Boshlash / menyu" },
      { command: "holat", description: "Bugungi davomatim" },
      { command: "pin", description: "PIN kodim" },
      { command: "admin", description: "Rahbariyat kirishi" },
      { command: "maktab", description: "Maktab nuqtasi (rahbariyat)" },
      { command: "yordam", description: "Yordam" },
    ];
    const O_CMD = [
      { command: "start", description: "Boshlash" },
      { command: "pin", description: "Kabinet PIN kodim" },
      { command: "holat", description: "Farzandim holati" },
    ];

    for (const [bot, token, qisqa, uzun, cmd] of [
      ["teach", TEACH, T_QISQA, T_UZUN, T_CMD],
      ["ota", OTA, O_QISQA, O_UZUN, O_CMD],
    ] as any[]) {
      if (!token) { natija[bot] = { xato: "token yo‘q" }; continue; }
      const r: any = {};
      for (const til of ["", "uz", "ru"]) {
        r["desc" + (til || "def")] = (await tg("setMyDescription", til ? { description: uzun, language_code: til } : { description: uzun }, token))?.ok;
        r["short" + (til || "def")] = (await tg("setMyShortDescription", til ? { short_description: qisqa, language_code: til } : { short_description: qisqa }, token))?.ok;
      }
      r.cmd = (await tg("setMyCommands", { commands: cmd }, token))?.ok;
      r.menu = (await tg("setChatMenuButton", { menu_button: { type: "web_app", text: "Kabinet", web_app: { url: APP } } }, token))?.ok;
      r.bot = (await tg("getMe", {}, token))?.result?.username ?? null;
      r.tekshir = (await tg("getMyShortDescription", {}, token))?.result?.short_description ?? null;
      natija[bot] = r;
    }
    return jsonc({ ok: true, ...natija });
  }
  if (q("sinf_sora") !== null) {
    if (!(await cronOk(q("sinf_sora")))) return no();
    const r = await davomatSoraYubor(QURUQ);
    return jsonc({ ok: true, ...r, quruq: QURUQ });
  }
  if (q("xulosa_eslatma") !== null) {
    if (!(await cronOk(q("xulosa_eslatma")))) return no();
    const d = await rpc("ep_xulosa_eslatma", {});
    const r: any[] = (d?.royxat ?? []) as any[]; let n = 0;
    const LOGO = SAYT + "sifat.png";
    for (const t of r) {
      const soni = QURUQ ? 1 : Number((await rpc("ep_eslatma_inc", { p_chat_id: t.chat_id, p_tur: "xulosa" })) ?? 1);
      const bosh = "🛡 <b>SIFAT NAZORATI</b> · EduNova School\n\n";
      let matn: string;
      if (soni <= 1) {
        matn = bosh + `Hurmatli <b>${esc(t.ism)}</b>, siz bugungi <b>dars xulosasini yozmagansiz</b>.\n\n` +
          `Iltimos, botga kiring va <b>📝 Xulosa yozish</b> tugmasi orqali xulosa yozing — <b>ota-onalar kutmoqda</b>.`;
      } else if (soni <= 3) {
        matn = bosh + `⚠️ <b>${soni}-eslatma.</b> ${esc(t.ism)}, dars xulosasi hali ham yozilmagan.\n\n` +
          `Ota-onalar bugungi dars haqida xabar ololmayapti. Hoziroq botga kirib yozing.`;
      } else {
        matn = bosh + `🚨 <b>Jiddiy ogohlantirish · ${soni}-eslatma</b>\n\n${esc(t.ism)}, xulosa yozilmagani rahbariyat hisobotiga tushdi va intizom buzilishi sifatida qayd etiladi.\n\nOta-onalar kutmoqda — hozir yozing.`;
      }
      if (QURUQ) { n++; continue; }
      const kb = { inline_keyboard: [[{ text: "📝 Xulosa yozish", callback_data: "xl_menu" }]] };
      let r2: any;
      if (soni <= 1) {
        r2 = await tg("sendPhoto", { chat_id: t.chat_id, photo: LOGO, caption: matn, parse_mode: "HTML", reply_markup: kb });
        if (!r2?.ok) r2 = await send(Number(t.chat_id), matn, { reply_markup: kb });
      } else {
        r2 = await send(Number(t.chat_id), matn, { reply_markup: kb });
      }
      if (r2?.ok) n++;
    }
    return jsonc({ ok: true, yuborildi: n, jami: r.length, quruq: QURUQ });
  }
  if (q("loksiz") !== null) {
    if (!(await cronOk(q("loksiz")))) return no();
    const d = await rpc("ep_teach_loksiz", {});
    const r: string[] = (d?.royxat ?? []) as string[];
    if (!r.length) return jsonc({ ok: true, yuborildi: 0, hammasi_yoqdi: true });
    const t = `\u26A0\uFE0F <b>Joylashuv yoqilmagan</b>\n${r.length} ta o\u2018qituvchi ikki eslatmadan keyin ham jonli joylashuvni yoqmadi:\n\n` +
      r.map((x) => "\u2022 " + esc(x)).join("\n");
    let n = 0;
    const adm = await rpc("ep_adminlar_chat", {});
    for (const c of (Array.isArray(adm) ? adm : [])) { if (!QURUQ) await send(Number(c), t); n++; }
    return jsonc({ ok: true, yuborildi: n, soni: r.length, quruq: QURUQ });
  }
  if (q("oqit_xulosa") !== null) {
    if (!(await cronOk(q("oqit_xulosa")))) return no();
    const t = await kimMaktabda(); let n = 0;
    const d = await rpc("ep_adminlar_chat", {});
    for (const c of (Array.isArray(d) ? d : [])) { if (!QURUQ) await send(Number(c), "🕗 <b>Ertalabki hisobot</b>\n\n" + t); n++; }
    return jsonc({ ok: true, yuborildi: n });
  }
  if (q("admin") !== null) {
    const b = await req.json().catch(() => ({})) as any;
    const d = await rpc("ep_teach_tasdiq", { p_token: b.token, p_ariza_id: b.ariza_id, p_ok: !!b.ok });
    if (d?.ok && d.chat_id) await send(Number(d.chat_id), d.holat === "tasdiqlandi" ? T.tasdiq(d.pin) : T.rad, d.holat === "tasdiqlandi" ? { reply_markup: KB_TEACH } : {});
    return jsonc(d ?? { ok: false });
  }
  if (req.method !== "POST") return new Response("teach-bot v3.4 ok", { headers: CORS });
  if (CRON && req.headers.get("x-telegram-bot-api-secret-token") !== CRON) return no();
  const upd = await req.json().catch(() => null); if (!upd) return new Response("ok");
  try {
    if (upd.callback_query) await callback(upd.callback_query);
    else { const msg = upd.message ?? upd.edited_message; if (msg) await xabar(msg); }
  } catch (e) { console.error("upd", String(e)); }
  return new Response("ok");
});
