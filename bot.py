/**
 * ╔══════════════════════════════════════════════════════════════╗
 * ║      🚀 SIFTNODES v8.1 — PREMIUM NODE.JS BOT              ║
 * ║  Tickets • AI • Payments (QR + AI Verify) • Plans • Promo    ║
 * ║      MC • Giveaway • Reviews • Permissions • Multi-Owner     ║
 * ╚══════════════════════════════════════════════════════════════╝
 */

require('dotenv').config();
const {
  Client, GatewayIntentBits, Partials, Collection,
  EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle,
  StringSelectMenuBuilder, ModalBuilder, TextInputBuilder,
  TextInputStyle, PermissionFlagsBits, ChannelType, ActivityType,
  AttachmentBuilder
} = require('discord.js');
const fs = require('fs');
const path = require('path');

// ═══ CONFIG ═══
const env = (k, d = null) => process.env[k] ?? d;
const envb = (k, d = false) => String(env(k, d)).toLowerCase() === 'true';
const envi = (k, d = 0) => { const n = parseInt(env(k, d)); return isNaN(n) ? d : n; };
const envc = (k, d = '5865F2') => { try { return parseInt(env(k, d), 16); } catch { return parseInt(d, 16); } };

// ═══ OWNER IDs (multi + auto-clean) ═══
const OWNER_IDS_RAW = env('OWNER_ID', '');
const OWNER_IDS = String(OWNER_IDS_RAW)
  .split(',')
  .map(x => x.trim().replace(/^["']|["']$/g, '').trim())
  .filter(x => /^\d{15,25}$/.test(x));
const OWNER_ID = OWNER_IDS[0] ? parseInt(OWNER_IDS[0]) : 0;

const TOKEN = (env('DISCORD_TOKEN', '') || '').trim().replace(/^["']|["']$/g, '');
const PREFIX = env('PREFIX', '!');
const BOT_NAME = env('BOT_NAME', 'SiftNodes');
const FOOTER = env('BOT_FOOTER_TEXT', 'SiftNodes • Premium Hosting');

const COLOR = {
  main: envc('EMBED_COLOR', '5865F2'),
  ok: envc('SUCCESS_COLOR', '57F287'),
  err: envc('ERROR_COLOR', 'ED4245'),
  warn: envc('WARN_COLOR', 'FEE75C'),
  gold: envc('GOLD_COLOR', 'FFD700'),
  info: envc('INFO_COLOR', '00B0F4'),
  premium: envc('PREMIUM_COLOR', 'FF69B4')
};

const AI_ENABLED = envb('AI_ENABLED', true);
const AI_TOKENS = envi('AI_MAX_TOKENS', 800);
const AI_TEMP = parseFloat(env('AI_TEMPERATURE', '0.7'));
const AI_HIST = envi('AI_HISTORY_LIMIT', 12);
const AI_PING = envb('AI_PING_ENABLED', true);
const AI_SCREENSHOT_VERIFY = envb('AI_SCREENSHOT_VERIFY', true);
const PAY_SYM = env('PAYMENT_CURRENCY_SYMBOL', '₹');
const AUTO_FEST = envb('AUTO_FESTIVAL', true);
let FEST_CH = envi('FESTIVAL_CHANNEL_ID', 0);
let MAINT = envb('MAINTENANCE_MODE', false);

// ═══ DATABASE ═══
const BASE_DIR = __dirname;
const DATA_DIR = path.join(BASE_DIR, 'data');
const BACKUP_DIR = path.join(BASE_DIR, 'backups');
const QR_PATH = path.join(BASE_DIR, 'qr.png');
[DATA_DIR, BACKUP_DIR].forEach(d => { if (!fs.existsSync(d)) fs.mkdirSync(d, { recursive: true }); });

const dbPath = n => path.join(DATA_DIR, `${n}.json`);
const load = (n, d = {}) => {
  try {
    const p = dbPath(n);
    if (!fs.existsSync(p)) return d;
    return JSON.parse(fs.readFileSync(p, 'utf8')) || d;
  } catch { return d; }
};
const save = (n, data) => {
  try {
    const tmp = dbPath(n) + '.tmp';
    fs.writeFileSync(tmp, JSON.stringify(data, null, 2), 'utf8');
    fs.renameSync(tmp, dbPath(n));
  } catch (e) { console.error(`save[${n}]:`, e.message); }
};

// ═══ CLIENT ═══
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds, GatewayIntentBits.GuildMembers,
    GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildMessageReactions, GatewayIntentBits.DirectMessages,
    GatewayIntentBits.GuildModeration
  ],
  partials: [Partials.Channel, Partials.Message, Partials.Reaction, Partials.User, Partials.GuildMember]
});

client.commands = new Collection();

// ═══ HELPERS ═══
const makeEmbed = (title = null, desc = null, color = COLOR.main) => {
  const e = new EmbedBuilder().setColor(color).setTimestamp(new Date());
  if (title) e.setTitle(title);
  if (desc) e.setDescription(desc);
  e.setFooter({ text: FOOTER, iconURL: client.user?.displayAvatarURL() });
  return e;
};

const ok = (m, t) => m.reply({ embeds: [makeEmbed('✅ Success', t, COLOR.ok)], allowedMentions: { repliedUser: false } });
const err = (m, t) => m.reply({ embeds: [makeEmbed('❌ Error', t, COLOR.err)], allowedMentions: { repliedUser: false } });
const warn = (m, t) => m.reply({ embeds: [makeEmbed('⚠️ Warning', t, COLOR.warn)], allowedMentions: { repliedUser: false } });

const parseTime = (s) => {
  const m = String(s).toLowerCase().match(/^(\d+)([smhd])$/);
  if (!m) return null;
  return parseInt(m[1]) * ({ s: 1, m: 60, h: 3600, d: 86400 }[m[2]] || 0);
};

const isOwner = (m) => OWNER_IDS.includes(m.author.id);
const isAdmin = (m) => m.member?.permissions?.has(PermissionFlagsBits.Administrator);
const rand = (a, b) => Math.floor(Math.random() * (b - a + 1)) + a;

const register = (name, opts, handler) => client.commands.set(name, { opts: opts || {}, handler });

// ═══ PERMISSION ═══
async function checkPermission(msg, opts) {
  if (opts.owner) {
    if (isOwner(msg)) return true;
    await err(msg, `🔒 **Owner only command.**\n\nYour ID: \`${msg.author.id}\`\nRun \`${PREFIX}whoami\` to check.`);
    return false;
  }
  if (opts.public) return true;
  if (isAdmin(msg) || isOwner(msg)) return true;
  await err(msg, '🔒 **Administrator only command.**\nOnly staff members can use this command. Members can only use AI commands.');
  return false;
}

// ═══ AI TEXT ═══
const aiHist = {};
const AI_SYSTEM = 'You are SiftNodes, a friendly helpful Discord assistant. Reply naturally, be conversational and match the user\'s language (Hindi, English or Hinglish). Keep replies concise and human.';

async function aiAsk(prompt, userId) {
  if (!AI_ENABLED) return '❌ AI disabled.';
  if (!aiHist[userId]) aiHist[userId] = [];
  aiHist[userId].push({ role: 'user', content: prompt });
  aiHist[userId] = aiHist[userId].slice(-AI_HIST);

  const headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://pollinations.ai/',
    'Content-Type': 'application/json'
  };
  const messages = [{ role: 'system', content: AI_SYSTEM }, ...aiHist[userId]];

  for (let i = 0; i < 2; i++) {
    try {
      const r = await fetch('https://text.pollinations.ai/openai', {
        method: 'POST', headers,
        body: JSON.stringify({ model: 'openai', messages, temperature: AI_TEMP, max_tokens: AI_TOKENS, stream: false, private: true })
      });
      if (r.ok) {
        const d = await r.json();
        const out = d?.choices?.[0]?.message?.content;
        if (out && out.trim().length > 1) { aiHist[userId].push({ role: 'assistant', content: out }); return out.trim(); }
      }
    } catch (e) { console.log('AI M1:', e.message); }
    await new Promise(r => setTimeout(r, 1200));
  }

  for (let i = 0; i < 2; i++) {
    try {
      const r = await fetch('https://text.pollinations.ai/', {
        method: 'POST', headers,
        body: JSON.stringify({ messages, model: 'openai', private: true, seed: rand(1, 999999) })
      });
      if (r.ok) {
        const out = (await r.text()).trim();
        if (out && out.length > 1 && !out.startsWith('{')) { aiHist[userId].push({ role: 'assistant', content: out }); return out; }
      }
    } catch (e) { console.log('AI M2:', e.message); }
    await new Promise(r => setTimeout(r, 1200));
  }

  try {
    const ctx = AI_SYSTEM + '\n\n' + aiHist[userId].map(m => `${m.role}: ${m.content}`).join('\n');
    const r = await fetch(`https://text.pollinations.ai/${encodeURIComponent(ctx.slice(0, 1800))}?model=openai&private=true`, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    if (r.ok) {
      const out = (await r.text()).trim();
      if (out) { aiHist[userId].push({ role: 'assistant', content: out }); return out; }
    }
  } catch (e) { console.log('AI M3:', e.message); }

  return '⚠️ AI thoda busy hai — dobara try kar.';
}

// ═══ AI VISION ═══
async function aiVerifyScreenshot(imageBuffer, expectedAmount, expectedMethod, product) {
  if (!AI_SCREENSHOT_VERIFY) return { skipped: true };
  try {
    if (!imageBuffer) return { error: 'no_image' };
    const base64 = imageBuffer.toString('base64');
    let mime = 'image/png';
    if (imageBuffer[0] === 0xFF && imageBuffer[1] === 0xD8) mime = 'image/jpeg';
    else if (imageBuffer[0] === 0x89 && imageBuffer[1] === 0x50) mime = 'image/png';
    else if (imageBuffer[0] === 0x47 && imageBuffer[1] === 0x49) mime = 'image/gif';
    const imageData = `data:${mime};base64,${base64}`;

    const prompt = `You are a payment verification assistant. Analyze this image carefully.

The user claims this is a payment screenshot with:
- Expected amount: ${PAY_SYM}${expectedAmount}
- Expected method: ${expectedMethod}
- Product: ${product}

Verify:
1. Is this actually a payment/transaction screenshot? (look for payment apps like Paytm, PhonePe, GPay, BHIM, bank apps, UPI apps)
2. Is a payment amount visible?
3. Does the amount match "${PAY_SYM}${expectedAmount}" (approximately)?
4. Is there any indication of successful payment (like "Success", "Paid", green checkmark, UTR number)?
5. Any signs of manipulation (edited text, wrong fonts, unusual UI)?

Reply ONLY in this exact JSON format, no other text:
{"is_payment_screenshot": true/false, "amount_visible": true/false, "amount_matches": true/false, "payment_success_indicated": true/false, "confidence": "high"/"medium"/"low", "verdict": "genuine"/"suspicious"/"fake"/"unclear", "notes": "brief 1-line observation"}`;

    const payload = {
      model: 'openai',
      messages: [{ role: 'user', content: [{ type: 'text', text: prompt }, { type: 'image_url', image_url: { url: imageData } }] }],
      temperature: 0.2, max_tokens: 400, private: true
    };
    const headers = { 'User-Agent': 'Mozilla/5.0', 'Referer': 'https://pollinations.ai/', 'Content-Type': 'application/json' };

    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        const r = await fetch('https://text.pollinations.ai/openai', { method: 'POST', headers, body: JSON.stringify(payload) });
        if (!r.ok) continue;
        const d = await r.json();
        const out = d?.choices?.[0]?.message?.content || '';
        console.log('[AI Verify raw]', out.slice(0, 300));
        const jsonMatch = out.match(/\{[\s\S]*?\}/);
        if (jsonMatch) {
          try { return JSON.parse(jsonMatch[0]); }
          catch (pe) { console.log('JSON parse fail:', pe.message); }
        }
        return { verdict: 'unclear', notes: out.slice(0, 200) || 'AI could not analyze' };
      } catch (e) { console.log('AI verify attempt fail:', e.message); }
      await new Promise(r => setTimeout(r, 1500));
    }
  } catch (e) { console.log('AI verify error:', e.message); }
  return { verdict: 'unclear', notes: 'AI verification unavailable' };
}

const getVerdictColor = (v) => v === 'genuine' ? COLOR.ok : v === 'suspicious' ? COLOR.warn : v === 'fake' ? COLOR.err : COLOR.info;
const getVerdictEmoji = (v) => v === 'genuine' ? '✅' : v === 'suspicious' ? '⚠️' : v === 'fake' ? '❌' : '❓';
const getVerdictText = (v) => v === 'genuine' ? 'Looks Genuine' : v === 'suspicious' ? 'Suspicious' : v === 'fake' ? 'Likely Fake' : 'Unclear';

// ═══ STATE ═══
const payments = load('payments', {});
const payCfg = load('pay_cfg', {});
const tickets = load('tickets', {});
const ticketCfg = load('ticket_cfg', {});
const plans = load('plans', {});
const promos = load('promos', {});
const links = load('links', {});
const anns = load('announcements', {});
const warns = load('warns', {});
const giveaways = load('giveaways', {});
const premiumData = load('premium', {});
const mc = load('minecraft', {});
const reviews = load('reviews', {});
const reviewCfg = load('review_cfg', {});

const pendingProofUpload = new Map();
const spamCache = new Map();

const findPayment = (pid) => {
  for (const uid in payments) {
    const r = payments[uid].find(x => x.id === pid);
    if (r) return { ownerUid: uid, rec: r };
  }
  return null;
};

async function fetchImageBuffer(url) {
  try {
    const res = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    if (!res.ok) return null;
    return Buffer.from(await res.arrayBuffer());
  } catch (e) { console.log('Fetch image fail:', e.message); return null; }
}

// ═══ INTERACTIONS ═══
client.on('interactionCreate', async (itx) => {
  try {
    if (itx.isButton()) return handleButton(itx);
    if (itx.isModalSubmit()) return handleModal(itx);
    if (itx.isStringSelectMenu()) return handleSelect(itx);
  } catch (e) {
    console.error('Interaction error:', e);
    if (!itx.replied && !itx.deferred) itx.reply({ content: `❌ \`${e.message}\``, ephemeral: true }).catch(() => {});
  }
});

async function handleButton(itx) {
  const id = itx.customId;

  if (id.startsWith('pay_verify_')) {
    const pid = id.replace('pay_verify_', '');
    const f = findPayment(pid);
    if (!f) return itx.reply({ content: '❌ Payment not found.', ephemeral: true });
    if (f.rec.status !== 'pending') return itx.reply({ content: `❌ Already ${f.rec.status}.`, ephemeral: true });
    if (f.rec.to !== itx.user.id) return itx.reply({ content: '❌ This payment is not for you.', ephemeral: true });

    pendingProofUpload.set(itx.user.id, pid);
    const e = makeEmbed('📸 Send Your Payment Screenshot', null, COLOR.info);
    e.setDescription('**Please drop your payment screenshot here in this DM.**\n\n📎 Attach the image directly.\n⏱️ You have 10 minutes.\n🔍 **AI verification enabled** — clearly show:\n  • Payment amount\n  • Payment method\n  • Success indication\n\n*Fake/edited screenshots will be auto-detected.*');
    await itx.reply({ embeds: [e] });

    setTimeout(() => { if (pendingProofUpload.get(itx.user.id) === pid) pendingProofUpload.delete(itx.user.id); }, 10 * 60 * 1000);
    return;
  }

  if (id.startsWith('owner_approve_')) {
    if (!OWNER_IDS.includes(itx.user.id)) return itx.reply({ content: '❌ Owner only.', ephemeral: true });
    const pid = id.replace('owner_approve_', '');
    const f = findPayment(pid);
    if (!f) return itx.reply({ content: '❌ Payment not found.', ephemeral: true });
    if (f.rec.status === 'verified') return itx.reply({ content: '✅ Already verified.', ephemeral: true });

    f.rec.status = 'verified'; f.rec.verified_by = itx.user.id; f.rec.verified_at = new Date().toISOString();
    save('payments', payments);
    await itx.reply({ embeds: [makeEmbed('✅ Payment Approved', `Payment \`${pid}\` approved.`, COLOR.ok)] });

    for (const tid of [f.rec.to, f.rec.from]) {
      try {
        const u = await client.users.fetch(String(tid));
        const dmE = makeEmbed('✅ Payment Verified', null, COLOR.ok);
        dmE.addFields({ name: 'Payment ID', value: `\`${pid}\``, inline: true }, { name: 'Amount', value: `${PAY_SYM}${f.rec.amount}`, inline: true }, { name: 'Product', value: f.rec.product || '—' });
        dmE.setDescription('Your payment has been verified successfully. 🎉');
        await u.send({ embeds: [dmE] });
      } catch {}
    }
    try {
      const oldEmbed = itx.message.embeds[0];
      if (oldEmbed) {
        const newE = EmbedBuilder.from(oldEmbed).setColor(COLOR.ok);
        newE.setFooter({ text: `${FOOTER} • ✅ Approved` });
        await itx.message.edit({ embeds: [newE], components: [] });
      }
    } catch {}
    return;
  }

  if (id.startsWith('owner_reject_')) {
    if (!OWNER_IDS.includes(itx.user.id)) return itx.reply({ content: '❌ Owner only.', ephemeral: true });
    const pid = id.replace('owner_reject_', '');
    const modal = new ModalBuilder().setCustomId(`owner_rejmodal_${pid}`).setTitle('❌ Reject Payment');
    modal.addComponents(new ActionRowBuilder().addComponents(
      new TextInputBuilder().setCustomId('reason').setLabel('Reason').setStyle(TextInputStyle.Paragraph).setRequired(true).setMaxLength(300)
    ));
    return itx.showModal(modal);
  }

  if (id === 'ticket_open') {
    const gid = itx.guild.id;
    const cfg = ticketCfg[gid] || {};
    try {
      const parent = cfg.category ? itx.guild.channels.cache.get(cfg.category) : null;
      const ch = await itx.guild.channels.create({
        name: `ticket-${itx.user.username}`.slice(0, 90),
        type: ChannelType.GuildText, parent: parent || null, topic: `Ticket by ${itx.user.id}`,
        permissionOverwrites: [
          { id: itx.guild.id, deny: [PermissionFlagsBits.ViewChannel] },
          { id: itx.user.id, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages, PermissionFlagsBits.ReadMessageHistory] },
          { id: client.user.id, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages, PermissionFlagsBits.ManageChannels] },
          ...(cfg.support_roles || []).map(r => ({ id: r, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages] }))
        ]
      });
      tickets[ch.id] = { user: itx.user.id, guild: itx.guild.id, created: new Date().toISOString(), claimed: null };
      save('tickets', tickets);
      const title = cfg.panel?.title || '🎫 Support Ticket';
      const e = makeEmbed(title, `Hey ${itx.user}, our team will be with you shortly.\nUse \`${PREFIX}ticket close\` to close.`, COLOR.ok);
      if (cfg.panel?.thumbnail) e.setThumbnail(cfg.panel.thumbnail);
      await ch.send({ content: `${itx.user}`, embeds: [e] });
      await itx.reply({ content: `✅ Ticket created: ${ch}`, ephemeral: true });
    } catch (x) { await itx.reply({ content: `❌ ${x.message}`, ephemeral: true }); }
    return;
  }

  if (id.startsWith('ticket_config_')) {
    if (!isAdmin(itx.member) && !OWNER_IDS.includes(itx.user.id)) return itx.reply({ content: '❌ Admin only.', ephemeral: true });
    const chId = id.replace('ticket_config_', '');
    const modal = new ModalBuilder().setCustomId(`ticketsetup_${chId}`).setTitle('🎫 Configure Ticket Panel');
    modal.addComponents(
      new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('title').setLabel('Panel Title').setStyle(TextInputStyle.Short).setValue('🎫 Support Center').setRequired(true).setMaxLength(200)),
      new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('desc').setLabel('Description').setStyle(TextInputStyle.Paragraph).setValue('Click below to open a support ticket.\nOur team will assist you shortly.').setRequired(true).setMaxLength(1000)),
      new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('color').setLabel('Color (hex, no #)').setStyle(TextInputStyle.Short).setValue('FFD700').setRequired(false).setMaxLength(6)),
      new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('thumb').setLabel('Thumbnail URL').setStyle(TextInputStyle.Short).setRequired(false).setMaxLength(500)),
      new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('banner').setLabel('Banner Image URL').setStyle(TextInputStyle.Short).setRequired(false).setMaxLength(500))
    );
    return itx.showModal(modal);
  }

  if (id === 'help_home') return itx.update({ embeds: [homeEmbed()], components: [helpRow(), helpButtons()] });
  if (id === 'help_close') return itx.message.delete().catch(() => {});
}

async function handleModal(itx) {
  const id = itx.customId;

  if (id.startsWith('owner_rejmodal_')) {
    const pid = id.replace('owner_rejmodal_', '');
    const f = findPayment(pid);
    if (!f) return itx.reply({ content: '❌ Not found.', ephemeral: true });
    const reason = itx.fields.getTextInputValue('reason');
    f.rec.status = 'rejected'; f.rec.reason = reason; f.rec.rejected_by = itx.user.id;
    save('payments', payments);
    await itx.reply({ embeds: [makeEmbed('❌ Payment Rejected', `\`${pid}\` rejected.`, COLOR.err)] });

    for (const tid of [f.rec.to, f.rec.from]) {
      try {
        const u = await client.users.fetch(String(tid));
        const dmE = makeEmbed('❌ Payment Rejected', null, COLOR.err);
        dmE.addFields({ name: 'Payment ID', value: `\`${pid}\``, inline: true }, { name: 'Reason', value: reason });
        await u.send({ embeds: [dmE] });
      } catch {}
    }
    try {
      const oldEmbed = itx.message?.embeds?.[0];
      if (oldEmbed) {
        const newE = EmbedBuilder.from(oldEmbed).setColor(COLOR.err);
        newE.setFooter({ text: `${FOOTER} • ❌ Rejected` });
        await itx.message.edit({ embeds: [newE], components: [] });
      }
    } catch {}
    return;
  }

  if (id.startsWith('ticketsetup_')) {
    const chId = id.replace('ticketsetup_', '');
    let color = COLOR.gold;
    try { color = parseInt(itx.fields.getTextInputValue('color').replace('#', '') || 'FFD700', 16); } catch {}
    const cfg = ticketCfg[itx.guild.id] || {};
    cfg.panel = {
      title: itx.fields.getTextInputValue('title'), desc: itx.fields.getTextInputValue('desc'), color,
      thumbnail: itx.fields.getTextInputValue('thumb').trim(), banner: itx.fields.getTextInputValue('banner').trim()
    };
    ticketCfg[itx.guild.id] = cfg;
    save('ticket_cfg', ticketCfg);
    const ch = itx.guild.channels.cache.get(chId);
    if (!ch) return itx.reply({ content: '❌ Channel not found.', ephemeral: true });
    const e = new EmbedBuilder().setTitle(cfg.panel.title).setDescription(cfg.panel.desc).setColor(color);
    if (cfg.panel.thumbnail) e.setThumbnail(cfg.panel.thumbnail);
    if (cfg.panel.banner) e.setImage(cfg.panel.banner);
    e.setFooter({ text: FOOTER, iconURL: client.user?.displayAvatarURL() });
    await ch.send({ embeds: [e], components: [ticketPanelRow()] });
    await itx.reply({ content: `✅ Panel deployed in ${ch}!`, ephemeral: true });
    return;
  }
}

async function handleSelect(itx) {
  const id = itx.customId;
  if (id === 'help_select') {
    const k = itx.values[0];
    const data = HELP_DATA[k];
    if (!data) return;
    const [title, color, cmds] = data;
    const e = new EmbedBuilder().setTitle(title).setDescription(`**${cmds.length}** commands available`).setColor(color)
      .setFooter({ text: `${BOT_NAME} • ${PREFIX}help`, iconURL: client.user.displayAvatarURL() });
    for (const [c, d] of cmds) e.addFields({ name: `\`${c}\``, value: d });
    return itx.update({ embeds: [e], components: itx.message.components });
  }
}

const ticketPanelRow = () => new ActionRowBuilder().addComponents(
  new ButtonBuilder().setCustomId('ticket_open').setLabel('📩 Open Ticket').setStyle(ButtonStyle.Primary)
);

// ═══ HELP MENU ═══
const HELP_DATA = {
  ai: ['🤖 AI System', 0x9B59B6, [
    [`@${BOT_NAME} <message>`, 'Ping bot for AI chat'],
    [`${PREFIX}ai <message>`, 'Direct AI chat'],
    [`${PREFIX}ai status`, 'AI status'],
    [`${PREFIX}ai reset`, 'Reset your AI history'],
  ]],
  tickets: ['🎫 Tickets', COLOR.gold, [
    [`${PREFIX}ticket setup <channel_id>`, 'Deploy ticket panel (admin)'],
    [`${PREFIX}ticket claim`, 'Claim current ticket'],
    [`${PREFIX}ticket close`, 'Close current ticket'],
    [`${PREFIX}ticket add @user`, 'Add user to ticket (admin)'],
    [`${PREFIX}ticket config`, 'Configure (admin)'],
  ]],
  payments: ['💳 Payments', COLOR.ok, [
    [`${PREFIX}pay <amt> <@user> <method> <product>`, 'Create payment request'],
    [`${PREFIX}pay-setup-log-channel <#ch>`, 'Set log channel (admin)'],
    [`${PREFIX}pay-setup-qr <UPI or URL>`, 'Set payment QR (admin)'],
    [`${PREFIX}pay-history [user]`, 'Payment history'],
  ]],
  plans: ['📋 Plans', 0x3498DB, [
    [`${PREFIX}plan-add <name> <price> <RAM> <CPU> <disk>`, 'Create plan (admin)'],
    [`${PREFIX}plan-remove <plan-id>`, 'Delete plan (admin)'],
    [`${PREFIX}plan-slot <slot> <plan-id>`, 'Assign slot (admin)'],
    [`${PREFIX}plan-list`, 'List all plans'],
    [`${PREFIX}plan-edit <plan-id> <field> <value>`, 'Edit plan (admin)'],
  ]],
  promo: ['🏷️ Promo', 0xE67E22, [
    [`${PREFIX}promo-create <code> <amt> <#ch> <expire>`, 'Create promo (admin)'],
    [`${PREFIX}promo-remove <code>`, 'Remove promo (admin)'],
    [`${PREFIX}promo-list`, 'List promos'],
    [`${PREFIX}promo-check <code>`, 'Check promo validity'],
  ]],
  links: ['🔗 Links', 0x1ABC9C, [
    [`${PREFIX}link-add <name> <url> [type]`, 'Add link (admin)'],
    [`${PREFIX}link-remove <id>`, 'Remove link (admin)'],
    [`${PREFIX}link-list`, 'List all links'],
    [`${PREFIX}link-edit <id> <field> <value>`, 'Edit link (admin)'],
  ]],
  welcome: ['👋 Welcome / Goodbye', 0xF1C40F, [
    [`${PREFIX}setup-welcome-channel <#ch>`, 'Set welcome channel (admin)'],
    [`${PREFIX}setup-goodbye-channel <#ch>`, 'Set goodbye channel (admin)'],
    [`${PREFIX}welcome-edit <field> <value>`, 'Edit welcome (admin)'],
    [`${PREFIX}welcome-preview`, 'Preview welcome'],
    [`${PREFIX}welcome-remove`, 'Disable welcome (admin)'],
  ]],
  announcements: ['📢 Announcements', 0xE74C3C, [
    [`${PREFIX}announcement <msg>`, 'Send announcement (admin)'],
    [`${PREFIX}ai-announcement <prompt>`, 'AI announcement (admin)'],
    [`${PREFIX}announcement-delete <id>`, 'Delete (admin)'],
    [`${PREFIX}announcement-list`, 'List announcements'],
  ]],
  protection: ['🛡️ Protection', 0x34495E, [
    [`${PREFIX}protection setup`, 'Initial setup (admin)'],
    [`${PREFIX}protection enable/disable`, 'Toggle (admin)'],
    [`${PREFIX}protection whitelist <@user>`, 'Whitelist (admin)'],
    [`${PREFIX}protection lockdown`, 'Lockdown (admin)'],
    [`${PREFIX}protection config`, 'View config'],
  ]],
  moderation: ['🔨 Moderation', 0x95A5A6, [
    [`${PREFIX}ban <@user> [reason]`, 'Ban member (admin)'],
    [`${PREFIX}kick <@user> [reason]`, 'Kick member (admin)'],
    [`${PREFIX}timeout <@user> <duration> [reason]`, 'Timeout (admin)'],
    [`${PREFIX}warn <@user> [reason]`, 'Warn member (admin)'],
    [`${PREFIX}clear <amount>`, 'Bulk delete (admin)'],
    [`${PREFIX}lock [#channel]`, 'Lock channel (admin)'],
    [`${PREFIX}unlock [#channel]`, 'Unlock channel (admin)'],
  ]],
  minecraft: ['⛏️ Minecraft', 0x7F8C8D, [
    [`${PREFIX}create-minecraft <RAM> <CPU> <disk> <@user>`, 'Create MC (admin)'],
    [`${PREFIX}minecraft list`, 'List servers'],
    [`${PREFIX}minecraft manage <id>`, 'Manage server'],
    [`${PREFIX}minecraft suspension <id>`, 'Suspend (admin)'],
    [`${PREFIX}minecraft delete <id>`, 'Delete (admin)'],
    [`${PREFIX}minecraft status <id>`, 'Server status'],
  ]],
  giveaway: ['🎁 Giveaway', 0xF39C12, [
    [`${PREFIX}gstart <time> <winners> <prize>`, 'Start giveaway (admin)'],
    [`${PREFIX}gend <msg-id>`, 'End early (admin)'],
    [`${PREFIX}greroll <msg-id>`, 'Reroll winner (admin)'],
    [`${PREFIX}glist`, 'List giveaways'],
  ]],
  review: ['⭐ Reviews', 0xFFD700, [
    [`${PREFIX}review <1-5> [comment]`, 'Submit a review'],
    [`${PREFIX}review-setup <#channel>`, 'Set review channel (admin)'],
    [`${PREFIX}review-stats`, 'View review stats'],
    [`${PREFIX}review-list`, 'List recent reviews'],
  ]],
  premium: ['💎 Premium', COLOR.premium, [
    [`${PREFIX}premium add <@user> <days>`, 'Grant premium (admin)'],
    [`${PREFIX}premium remove <@user>`, 'Revoke premium (admin)'],
    [`${PREFIX}premium check <@user>`, 'Check status (admin)'],
  ]],
  owner: ['👑 Owner', 0xFF0000, [
    [`${PREFIX}whoami`, 'Show your ID and owner status'],
    [`${PREFIX}auto-roll <@role>`, 'Auto-role on join (admin)'],
    [`${PREFIX}auto-roll_remove`, 'Remove auto-role (admin)'],
    [`${PREFIX}owner status`, 'Bot status (owner)'],
    [`${PREFIX}owner maintenance <on/off>`, 'Maintenance (owner)'],
  ]]
};

function helpRow() {
  const opts = Object.entries(HELP_DATA).map(([k, [t, _, cmds]]) => {
    const parts = t.split(' ');
    return { label: parts.slice(1).join(' ').slice(0, 100), value: k, emoji: parts[0], description: `${cmds.length} commands` };
  });
  return new ActionRowBuilder().addComponents(
    new StringSelectMenuBuilder().setCustomId('help_select').setPlaceholder('📂  Choose a category to explore…').addOptions(opts)
  );
}

function helpButtons() {
  return new ActionRowBuilder().addComponents(
    new ButtonBuilder().setCustomId('help_home').setLabel('Home').setEmoji('🏠').setStyle(ButtonStyle.Secondary),
    new ButtonBuilder().setCustomId('help_close').setLabel('Close').setEmoji('❌').setStyle(ButtonStyle.Danger)
  );
}

function homeEmbed() {
  const e = new EmbedBuilder().setTitle(`⚡ ${BOT_NAME} — Premium Bot`).setColor(COLOR.gold).setTimestamp(new Date());
  e.setDescription(
    `Welcome to **${BOT_NAME}**!\n\n` +
    `🔧 **Prefix:** \`${PREFIX}\`\n` +
    `📂 Use the dropdown below\n` +
    `🤖 Mention me for AI: \`@${BOT_NAME} hi\`\n` +
    `🔍 **AI Screenshot Verification:** ${AI_SCREENSHOT_VERIFY ? '✅ Enabled' : '❌ Disabled'}\n` +
    `📊 Categories: **${Object.keys(HELP_DATA).length}**`
  );
  e.addFields(
    { name: '🤖 AI', value: `\`${PREFIX}ai <msg>\``, inline: true },
    { name: '💳 Payments', value: `\`${PREFIX}pay\``, inline: true },
    { name: '⭐ Reviews', value: `\`${PREFIX}review <1-5>\``, inline: true },
    { name: '🎫 Support', value: `\`${PREFIX}ticket\``, inline: true }
  );
  e.setThumbnail(client.user?.displayAvatarURL());
  return e;
}

// ═══ COMMANDS ═══

register('help', { public: true }, async (msg) => {
  await msg.reply({ embeds: [homeEmbed()], components: [helpRow(), helpButtons()] });
});

// ═══ WHOAMI (debug) ═══
register('whoami', { public: true }, async (msg) => {
  const uid = msg.author.id;
  const isOwn = OWNER_IDS.includes(uid);
  const e = makeEmbed('🪪 Who Am I?', null, isOwn ? COLOR.ok : COLOR.info);
  e.addFields(
    { name: '👤 Username', value: `\`${msg.author.tag || msg.author.username}\``, inline: true },
    { name: '🆔 Your ID', value: `\`${uid}\``, inline: true },
    { name: '📏 Length', value: `\`${uid.length}\` digits`, inline: true },
    { name: '👑 Owner?', value: isOwn ? '✅ Yes — you are the owner!' : '❌ No', inline: true },
    { name: '🛡️ Admin?', value: isAdmin(msg) ? '✅ Yes' : '❌ No', inline: true },
    { name: '📋 Owner IDs Loaded', value: OWNER_IDS.length ? OWNER_IDS.map(id => `\`${id}\``).join('\n') : '⚠️ None loaded', inline: false }
  );
  if (!isOwn && OWNER_IDS.length) {
    e.addFields({ name: '💡 Fix', value: `Add your ID to \`.env\` as:\n\`\`\`\nOWNER_ID=${uid}\n\`\`\`\nThen restart the bot.` });
  }
  if (!OWNER_IDS.length) {
    e.addFields({ name: '⚠️ No Owner IDs Found', value: `Your \`.env\` file might have a formatting issue.\nPlease set:\n\`\`\`\nOWNER_ID=${uid}\n\`\`\`\nThen restart.` });
  }
  return msg.reply({ embeds: [e] });
});

// ═══ AI ═══
register('ai', { public: true, sub: true }, async (msg, args) => {
  const sub = (args[0] || '').toLowerCase();
  if (sub === 'status') {
    const e = makeEmbed('🤖 AI Status', null, COLOR.info);
    e.addFields(
      { name: 'Text AI', value: '`openai`', inline: true },
      { name: 'Screenshot Verify', value: AI_SCREENSHOT_VERIFY ? '✅ On' : '❌ Off', inline: true },
      { name: 'Active Users', value: String(Object.keys(aiHist).length), inline: true }
    );
    return msg.reply({ embeds: [e] });
  }
  if (sub === 'reset') { delete aiHist[msg.author.id]; return ok(msg, 'Your AI history has been reset.'); }
  const prompt = args.join(' ');
  if (!prompt) return err(msg, `Usage: \`${PREFIX}ai <message>\``);

  const thinking = await msg.reply({ embeds: [makeEmbed('🤖 Thinking…', '⏳ Please wait a moment…', COLOR.info)] });
  try {
    const ans = await aiAsk(prompt, msg.author.id);
    await thinking.edit({ content: ans.slice(0, 1990) || '…', embeds: [] });
  } catch (e) {
    await thinking.edit({ embeds: [makeEmbed('❌ AI Error', `\`${e.message}\``, COLOR.err)], content: '' });
  }
});

register('ticket', { public: true, sub: true }, async (msg, args) => {
  const sub = (args[0] || '').toLowerCase();
  const rest = args.slice(1);
  if (!sub) return msg.reply({ embeds: [makeEmbed('🎫 Ticket System', `\`${PREFIX}ticket setup <channel_id>\` (admin)\n\`${PREFIX}ticket claim\`\n\`${PREFIX}ticket close\`\n\`${PREFIX}ticket add @user\`\n\`${PREFIX}ticket config\` (admin)`, COLOR.gold)] });

  if (sub === 'setup') {
    if (!isAdmin(msg) && !isOwner(msg)) return err(msg, 'Admin only.');
    const cid = (rest[0] || '').replace(/[<#>]/g, '');
    const ch = msg.guild.channels.cache.get(cid);
    if (!ch) return err(msg, `Channel not found. Usage: \`${PREFIX}ticket setup <channel_id>\``);
    const row = new ActionRowBuilder().addComponents(
      new ButtonBuilder().setCustomId(`ticket_config_${cid}`).setLabel('🎨 Configure Panel').setStyle(ButtonStyle.Primary)
    );
    return msg.reply({ embeds: [makeEmbed('🎫 Ticket Panel Setup', `**Target:** ${ch}\n\nClick button below to configure.`, COLOR.gold)], components: [row] });
  }
  if (sub === 'claim') {
    if (!tickets[msg.channel.id]) return err(msg, 'Not a ticket channel.');
    tickets[msg.channel.id].claimed = msg.author.id; save('tickets', tickets);
    return msg.channel.send({ embeds: [makeEmbed('🙋 Claimed', `${msg.author} claimed this ticket.`, COLOR.ok)] });
  }
  if (sub === 'close') {
    if (!tickets[msg.channel.id]) return err(msg, 'Not a ticket channel.');
    await msg.channel.send({ embeds: [makeEmbed('🔒 Closing', 'Deleted in 5 seconds…', COLOR.warn)] });
    delete tickets[msg.channel.id]; save('tickets', tickets);
    setTimeout(() => msg.channel.delete().catch(() => {}), 5000);
    return;
  }
  if (sub === 'add') {
    if (!isAdmin(msg) && !isOwner(msg)) return err(msg, 'Admin only.');
    if (!tickets[msg.channel.id]) return err(msg, 'Not a ticket channel.');
    const u = msg.mentions.members.first();
    if (!u) return err(msg, 'Mention a user.');
    await msg.channel.permissionOverwrites.edit(u, { ViewChannel: true, SendMessages: true, ReadMessageHistory: true });
    return ok(msg, `Added ${u}.`);
  }
  if (sub === 'config') {
    if (!isAdmin(msg) && !isOwner(msg)) return err(msg, 'Admin only.');
    const key = (rest[0] || '').toLowerCase();
    const value = rest.slice(1).join(' ');
    const cfg = ticketCfg[msg.guild.id] || { category: null, support_roles: [] };
    if (!key) return msg.reply({ embeds: [makeEmbed('⚙️ Ticket Config', `**Category:** ${cfg.category ? `<#${cfg.category}>` : '—'}\n**Support:** ${(cfg.support_roles || []).map(r => `<@&${r}>`).join(', ') || '—'}`)] });
    if (key === 'category' && value) cfg.category = value.replace(/[<#>]/g, '');
    else if (key === 'support' && value) cfg.support_roles = [...(cfg.support_roles || []), value.replace(/[<@&>]/g, '')];
    else return err(msg, `Usage: \`${PREFIX}ticket config <category|support> <value>\``);
    ticketCfg[msg.guild.id] = cfg; save('ticket_cfg', ticketCfg);
    return ok(msg, `Updated \`${key}\`.`);
  }
});

register('pay', { public: true }, async (msg, args) => {
  const amount = args[0];
  const user = msg.mentions.users.first();
  const method = (args[2] || 'upi').toLowerCase();
  const product = args.slice(3).join(' ') || '—';

  if (!amount || !user) return err(msg, `**Usage:** \`${PREFIX}pay <amount> <@user> <method> <product>\``);
  if (user.bot) return err(msg, 'Cannot send payment to a bot.');
  if (user.id === msg.author.id) return err(msg, 'Cannot send payment to yourself.');
  if (!['upi', 'card', 'paypal', 'crypto', 'bank'].includes(method)) return err(msg, 'Invalid method. Use: `upi`, `card`, `paypal`, `crypto`, `bank`');

  const pid = `PAY-${rand(100000, 999999)}`;
  const uid = msg.author.id;
  const rec = { id: pid, amount, to: user.id, from: uid, method, product, guild: msg.guild.id, status: 'pending', time: new Date().toISOString() };
  if (!payments[uid]) payments[uid] = [];
  payments[uid].push(rec); save('payments', payments);

  const e = makeEmbed('💳 Payment Request Created', null, COLOR.ok);
  e.addFields(
    { name: 'ID', value: `\`${pid}\``, inline: true }, { name: 'Amount', value: `${PAY_SYM}${amount}`, inline: true },
    { name: 'Method', value: method.toUpperCase(), inline: true }, { name: 'From', value: `${msg.author}`, inline: true },
    { name: 'To', value: `${user}`, inline: true }, { name: 'Product', value: product, inline: true }
  );
  await msg.reply({ embeds: [e] });

  let dmOk = false;
  try {
    const dmE = makeEmbed('💳 New Payment Request', null, COLOR.gold);
    dmE.setDescription(`**You have received a payment request!**\n\n💰 **Amount:** ${PAY_SYM}${amount}\n📦 **Product:** ${product}\n💳 **Method:** ${method.toUpperCase()}\n👤 **From:** ${msg.author.username}\n🏠 **Server:** ${msg.guild.name}`);
    dmE.addFields(
      { name: '📋 Payment ID', value: `\`${pid}\`` },
      { name: '📝 How to proceed?', value: `1️⃣ Pay **${PAY_SYM}${amount}** using **${method.toUpperCase()}**\n2️⃣ Click **✅ Verify Payment** below\n3️⃣ Send your payment screenshot in DM\n4️⃣ Wait for admin approval` }
    );
    const row = new ActionRowBuilder().addComponents(
      new ButtonBuilder().setCustomId(`pay_verify_${pid}`).setLabel('✅ Verify Payment').setStyle(ButtonStyle.Success)
    );

    if (fs.existsSync(QR_PATH)) {
      const attachment = new AttachmentBuilder(QR_PATH, { name: 'payment-qr.png' });
      dmE.setImage('attachment://payment-qr.png');
      await user.send({ embeds: [dmE], components: [row], files: [attachment] });
    } else {
      const qrCfg = payCfg[msg.guild.id]?.qr;
      if (qrCfg) {
        try {
          const qrUrl = qrCfg.startsWith('http') ? qrCfg : `https://api.qrserver.com/v1/create-qr-code/?size=500x500&data=${encodeURIComponent(qrCfg)}`;
          const buf = await fetchImageBuffer(qrUrl);
          if (buf) {
            const attachment = new AttachmentBuilder(buf, { name: 'payment-qr.png' });
            dmE.setImage('attachment://payment-qr.png');
            await user.send({ embeds: [dmE], components: [row], files: [attachment] });
          } else { dmE.setImage(qrUrl); await user.send({ embeds: [dmE], components: [row] }); }
        } catch (er) { console.log('QR fail:', er.message); await user.send({ embeds: [dmE], components: [row] }); }
      } else { await user.send({ embeds: [dmE], components: [row] }); }
    }
    dmOk = true;
  } catch (x) { console.log('DM err:', x.message); }

  const logId = payCfg[msg.guild.id]?.log_channel;
  if (logId) {
    const ch = msg.guild.channels.cache.get(logId);
    if (ch) {
      const le = makeEmbed('💳 Payment Log', null, COLOR.info);
      le.addFields({ name: 'ID', value: `\`${pid}\``, inline: true }, { name: 'Amount', value: `${PAY_SYM}${amount}`, inline: true }, { name: 'DM', value: dmOk ? '✅' : '❌', inline: true });
      ch.send({ embeds: [le] }).catch(() => {});
    }
  }
  if (!dmOk) msg.channel.send({ embeds: [makeEmbed('⚠️ DM Failed', `${user} has DMs disabled.`, COLOR.warn)] });
});

register('pay-setup-log-channel', { admin: true }, async (msg, args) => {
  const ch = msg.mentions.channels.first() || msg.guild.channels.cache.get(args[0]);
  if (!ch) return err(msg, 'Mention a channel.');
  if (!payCfg[msg.guild.id]) payCfg[msg.guild.id] = {};
  payCfg[msg.guild.id].log_channel = ch.id; save('pay_cfg', payCfg);
  return ok(msg, `Log channel set to ${ch}.`);
});

register('pay-setup-qr', { admin: true }, async (msg, args) => {
  const v = args.join(' ');
  if (!v) return err(msg, `Usage: \`${PREFIX}pay-setup-qr <UPI or URL>\``);
  if (!payCfg[msg.guild.id]) payCfg[msg.guild.id] = {};
  payCfg[msg.guild.id].qr = v; save('pay_cfg', payCfg);
  const img = v.startsWith('http') ? v : `https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=${encodeURIComponent(v)}`;
  const e = makeEmbed('💳 Payment QR Configured', `**UPI:** \`${v}\``); e.setImage(img);
  return msg.reply({ embeds: [e] });
});

register('pay-history', { public: true }, async (msg) => {
  const user = msg.mentions.users.first() || msg.author;
  const hist = payments[user.id] || [];
  if (!hist.length) return err(msg, 'No payment history.');
  const e = makeEmbed(`💳 History — ${user.username}`);
  for (const r of hist.slice(-10)) e.addFields({ name: `\`${r.id}\` — ${PAY_SYM}${r.amount}`, value: `Status: **${r.status}** • ${r.method}` });
  return msg.reply({ embeds: [e] });
});

register('plan-add', { admin: true }, async (msg, args) => {
  const [name, price, ram, cpu, disk] = args;
  if (!name || !price || !ram || !cpu || !disk) return err(msg, `Usage: \`${PREFIX}plan-add <name> <price> <RAM> <CPU> <disk>\``);
  const gid = msg.guild.id;
  if (!plans[gid]) plans[gid] = {};
  const pid = `PLAN-${rand(100, 999)}`;
  plans[gid][pid] = { id: pid, name, price, ram, cpu, disk, slots: 0 };
  save('plans', plans);
  return ok(msg, `Plan \`${pid}\` — **${name}** created.`);
});
register('plan-remove', { admin: true }, async (msg, args) => {
  if (!plans[msg.guild.id]?.[args[0]]) return err(msg, 'Not found.');
  delete plans[msg.guild.id][args[0]]; save('plans', plans);
  return ok(msg, 'Removed.');
});
register('plan-list', { public: true }, async (msg) => {
  const lst = plans[msg.guild.id] || {};
  if (!Object.keys(lst).length) return err(msg, 'No plans.');
  const e = makeEmbed('📋 Available Plans');
  for (const p of Object.values(lst)) e.addFields({ name: `\`${p.id}\` — ${p.name}`, value: `₹${p.price} • ${p.ram}/${p.cpu}/${p.disk} • Slots: ${p.slots}` });
  return msg.reply({ embeds: [e] });
});
register('plan-slot', { admin: true }, async (msg, args) => {
  if (!plans[msg.guild.id]?.[args[1]]) return err(msg, 'Not found.');
  plans[msg.guild.id][args[1]].slots = parseInt(args[0]) || 0; save('plans', plans);
  return ok(msg, `Slots set to ${args[0]}.`);
});
register('plan-edit', { admin: true }, async (msg, args) => {
  const p = plans[msg.guild.id]?.[args[0]];
  if (!p) return err(msg, 'Not found.');
  const f = args[1], v = args.slice(2).join(' ');
  if (!['name', 'price', 'ram', 'cpu', 'disk', 'slots'].includes(f)) return err(msg, 'Invalid field.');
  p[f] = f === 'slots' ? parseInt(v) : v; save('plans', plans);
  return ok(msg, 'Updated.');
});

register('promo-create', { admin: true }, async (msg, args) => {
  const code = args[0], amount = args[1];
  const ch = msg.mentions.channels.first();
  if (!code || !amount || !ch) return err(msg, `Usage: \`${PREFIX}promo-create <code> <amount> <#channel> <expire>\``);
  if (!promos[msg.guild.id]) promos[msg.guild.id] = {};
  promos[msg.guild.id][code.toUpperCase()] = { code: code.toUpperCase(), amount, channel: ch.id, expire: args[3] || 'never', uses: 0 };
  save('promos', promos);
  return ok(msg, `Promo \`${code.toUpperCase()}\` created.`);
});
register('promo-remove', { admin: true }, async (msg, args) => {
  const c = args[0]?.toUpperCase();
  if (!promos[msg.guild.id]?.[c]) return err(msg, 'Not found.');
  delete promos[msg.guild.id][c]; save('promos', promos);
  return ok(msg, 'Removed.');
});
register('promo-list', { public: true }, async (msg) => {
  const lst = promos[msg.guild.id] || {};
  if (!Object.keys(lst).length) return err(msg, 'No promos.');
  const e = makeEmbed('🏷️ Active Promos');
  for (const [c, p] of Object.entries(lst)) e.addFields({ name: c, value: `Amount: ${p.amount} • Expire: ${p.expire}` });
  return msg.reply({ embeds: [e] });
});
register('promo-check', { public: true }, async (msg, args) => {
  const c = args[0]?.toUpperCase();
  const p = promos[msg.guild.id]?.[c];
  if (!p) return err(msg, 'Invalid promo.');
  return ok(msg, `\`${c}\` is valid — Amount: ${p.amount}`);
});

register('link-add', { admin: true }, async (msg, args) => {
  const [name, url, type] = args;
  if (!name || !url) return err(msg, `Usage: \`${PREFIX}link-add <name> <url> [type]\``);
  if (!links[msg.guild.id]) links[msg.guild.id] = {};
  const lid = `LNK-${rand(100, 999)}`;
  links[msg.guild.id][lid] = { id: lid, name, url, type: type || 'general' };
  save('links', links);
  return ok(msg, `Link \`${lid}\` added.`);
});
register('link-remove', { admin: true }, async (msg, args) => {
  if (!links[msg.guild.id]?.[args[0]]) return err(msg, 'Not found.');
  delete links[msg.guild.id][args[0]]; save('links', links);
  return ok(msg, 'Removed.');
});
register('link-list', { public: true }, async (msg) => {
  const lst = links[msg.guild.id] || {};
  if (!Object.keys(lst).length) return err(msg, 'No links.');
  const e = makeEmbed('🔗 Saved Links');
  for (const l of Object.values(lst)) e.addFields({ name: `\`${l.id}\` — ${l.name}`, value: `[${l.url}](${l.url})` });
  return msg.reply({ embeds: [e] });
});
register('link-edit', { admin: true }, async (msg, args) => {
  const l = links[msg.guild.id]?.[args[0]];
  if (!l) return err(msg, 'Not found.');
  const f = args[1], v = args.slice(2).join(' ');
  if (!['name', 'url', 'type'].includes(f)) return err(msg, 'Invalid.');
  l[f] = v; save('links', links);
  return ok(msg, 'Updated.');
});

register('setup-welcome-channel', { admin: true }, async (msg) => {
  const ch = msg.mentions.channels.first();
  if (!ch) return err(msg, 'Mention a channel.');
  const w = load('welcome', {}); w[msg.guild.id] = w[msg.guild.id] || {}; w[msg.guild.id].channel = ch.id;
  save('welcome', w);
  return ok(msg, `Welcome channel set to ${ch}.`);
});
register('setup-goodbye-channel', { admin: true }, async (msg) => {
  const ch = msg.mentions.channels.first();
  if (!ch) return err(msg, 'Mention a channel.');
  const g = load('goodbye', {}); g[msg.guild.id] = g[msg.guild.id] || {}; g[msg.guild.id].channel = ch.id;
  save('goodbye', g);
  return ok(msg, `Goodbye channel set to ${ch}.`);
});
register('welcome-edit', { admin: true }, async (msg, args) => {
  const k = (args[0] || '').toLowerCase(); const v = args.slice(1).join(' ');
  if (!['title', 'desc', 'gif'].includes(k)) return err(msg, 'Fields: `title`, `desc`, `gif`');
  const w = load('welcome', {}); w[msg.guild.id] = w[msg.guild.id] || {}; w[msg.guild.id][k] = v;
  save('welcome', w);
  return ok(msg, `Welcome \`${k}\` updated.`);
});
register('welcome-remove', { admin: true }, async (msg) => {
  const w = load('welcome', {}); delete w[msg.guild.id]; save('welcome', w);
  return ok(msg, 'Welcome disabled.');
});
register('welcome-preview', { public: true }, async (msg) => {
  const c = load('welcome', {})[msg.guild.id];
  if (!c) return err(msg, 'Not configured.');
  const e = new EmbedBuilder().setColor(COLOR.main)
    .setTitle((c.title || `Welcome ${msg.author.username}!`).replace('{user}', msg.author.username).replace('{guild}', msg.guild.name))
    .setDescription((c.desc || `Hey ${msg.author}, welcome to **${msg.guild.name}**!`).replace('{user}', `${msg.author}`).replace('{guild}', msg.guild.name));
  if (c.gif) e.setImage(c.gif);
  e.setThumbnail(msg.author.displayAvatarURL());
  return msg.reply({ embeds: [e] });
});

register('announcement', { admin: true }, async (msg, args) => {
  const text = args.join(' ');
  if (!text) return err(msg, 'Provide a message.');
  const e = makeEmbed('📢 Announcement', text);
  e.setAuthor({ name: msg.guild.name, iconURL: msg.guild.iconURL() || undefined });
  const m = await msg.channel.send({ content: '@everyone', embeds: [e] });
  anns[m.id] = { channel: msg.channel.id, content: text }; save('announcements', anns);
});
register('ai-announcement', { admin: true }, async (msg, args) => {
  const text = args.join(' ');
  if (!text) return err(msg, 'Provide a prompt.');
  const thinking = await msg.reply({ embeds: [makeEmbed('🤖 AI Announcement', '⏳ Generating…', COLOR.info)] });
  const out = await aiAsk(`Write a short, attractive Discord announcement about: ${text}`, msg.author.id);
  await thinking.delete().catch(() => {});
  const e = makeEmbed('📢 Announcement', out);
  e.setAuthor({ name: msg.guild.name, iconURL: msg.guild.iconURL() || undefined });
  const m = await msg.channel.send({ content: '@everyone', embeds: [e] });
  anns[m.id] = { channel: msg.channel.id, content: out }; save('announcements', anns);
});
register('announcement-delete', { admin: true }, async (msg, args) => {
  const r = anns[args[0]];
  if (!r) return err(msg, 'Not found.');
  delete anns[args[0]]; save('announcements', anns);
  const ch = msg.guild.channels.cache.get(r.channel);
  if (ch) try { const m = await ch.messages.fetch(args[0]); await m.delete(); } catch {}
  return ok(msg, 'Deleted.');
});
register('announcement-list', { public: true }, async (msg) => {
  if (!Object.keys(anns).length) return err(msg, 'None.');
  const e = makeEmbed('📢 Saved');
  for (const [id, r] of Object.entries(anns).slice(-10)) e.addFields({ name: `\`${id}\``, value: r.content.slice(0, 80) });
  return msg.reply({ embeds: [e] });
});

register('protection', { admin: true, sub: true }, async (msg, args) => {
  const gid = msg.guild.id;
  const data = load('protection', {});
  const cfg = data[gid] = data[gid] || { enabled: false, anti_spam: true, anti_link: false, anti_invite: true, whitelist: [], lockdown: false };
  const a = (args[0] || '').toLowerCase();
  const value = args.slice(1).join(' ');
  if (!a) return err(msg, `\`${PREFIX}protection <setup|enable|disable|whitelist|lockdown|config>\``);
  if (a === 'setup') { save('protection', data); return ok(msg, 'Configured.'); }
  if (a === 'enable') { cfg.enabled = true; save('protection', data); return ok(msg, '**ENABLED**'); }
  if (a === 'disable') { cfg.enabled = false; save('protection', data); return ok(msg, '**DISABLED**'); }
  if (a === 'config') return msg.reply({ embeds: [makeEmbed('⚙️ Protection', `Enabled: ${cfg.enabled}\nSpam: ${cfg.anti_spam}\nLink: ${cfg.anti_link}\nInvite: ${cfg.anti_invite}\nLockdown: ${cfg.lockdown}`)] });
  if (a === 'whitelist') {
    if (value) {
      const uid = value.replace(/[<@!&>]/g, '');
      if (!cfg.whitelist.includes(uid)) { cfg.whitelist.push(uid); save('protection', data); return ok(msg, `WL <@${uid}>`); }
      return err(msg, 'Already.');
    }
    return msg.reply({ embeds: [makeEmbed('🛡️ WL', cfg.whitelist.map(u => `<@${u}>`).join('\n') || 'Empty')] });
  }
  if (a === 'lockdown') {
    cfg.lockdown = !cfg.lockdown; save('protection', data);
    for (const ch of msg.guild.channels.cache.values()) {
      if (ch.type !== ChannelType.GuildText) continue;
      try { await ch.permissionOverwrites.edit(msg.guild.roles.everyone, { SendMessages: !cfg.lockdown }); } catch {}
    }
    return ok(msg, `Lockdown **${cfg.lockdown ? 'ON' : 'OFF'}**`);
  }
});

register('ban', { admin: true }, async (msg) => {
  const u = msg.mentions.members.first();
  if (!u) return err(msg, 'Mention a user.');
  await u.ban({ reason: msg.content.split(' ').slice(2).join(' ') || 'No reason' });
  return ok(msg, `Banned **${u.user.tag}**.`);
});
register('kick', { admin: true }, async (msg) => {
  const u = msg.mentions.members.first();
  if (!u) return err(msg, 'Mention a user.');
  await u.kick(msg.content.split(' ').slice(2).join(' ') || 'No reason');
  return ok(msg, `Kicked **${u.user.tag}**.`);
});
register('timeout', { admin: true }, async (msg, args) => {
  const u = msg.mentions.members.first();
  if (!u) return err(msg, 'Mention a user.');
  const s = parseTime(args[1]);
  if (!s) return err(msg, 'Duration: `10m`, `2h`, `3d`');
  await u.timeout(s * 1000, args.slice(2).join(' ') || 'No reason');
  return ok(msg, `Timed out **${u.user.tag}** for ${args[1]}.`);
});
register('warn', { admin: true }, async (msg, args) => {
  const u = msg.mentions.members.first();
  if (!u) return err(msg, 'Mention a user.');
  if (!warns[u.id]) warns[u.id] = [];
  warns[u.id].push({ reason: args.slice(1).join(' ') || 'No reason', by: msg.author.id, time: new Date().toISOString() });
  save('warns', warns);
  return ok(msg, `Warned **${u.user.tag}** (${warns[u.id].length}).`);
});
register('clear', { admin: true }, async (msg, args) => {
  const n = Math.min(parseInt(args[0]) || 10, 100);
  const d = await msg.channel.bulkDelete(n + 1, true);
  const m = await msg.channel.send({ embeds: [makeEmbed('🧹 Cleared', `Deleted **${d.size - 1}**.`, COLOR.ok)] });
  setTimeout(() => m.delete().catch(() => {}), 3000);
});
register('lock', { admin: true }, async (msg) => {
  const ch = msg.mentions.channels.first() || msg.channel;
  await ch.permissionOverwrites.edit(msg.guild.roles.everyone, { SendMessages: false });
  return ok(msg, `Locked ${ch}.`);
});
register('unlock', { admin: true }, async (msg) => {
  const ch = msg.mentions.channels.first() || msg.channel;
  await ch.permissionOverwrites.edit(msg.guild.roles.everyone, { SendMessages: null });
  return ok(msg, `Unlocked ${ch}.`);
});

register('create-minecraft', { admin: true }, async (msg, args) => {
  const [ram, cpu, disk] = args;
  const user = msg.mentions.users.first();
  if (!ram || !cpu || !disk || !user) return err(msg, `Usage: \`${PREFIX}create-minecraft <RAM> <CPU> <disk> <@user>\``);
  const sid = `MC-${rand(1000, 9999)}`;
  const exp = new Date(Date.now() + 30 * 86400000);
  mc[sid] = { user: user.id, ram, cpu, disk, expires: exp.toISOString(), suspended: false, created: new Date().toISOString() };
  save('minecraft', mc);
  const e = makeEmbed('⛏️ MC Server Created', null, COLOR.ok);
  e.addFields({ name: 'ID', value: `\`${sid}\``, inline: true }, { name: 'Owner', value: user.toString(), inline: true }, { name: 'Specs', value: `${ram} • ${cpu} • ${disk}` }, { name: 'Expires', value: `<t:${Math.floor(exp.getTime() / 1000)}:R>` });
  await msg.reply({ embeds: [e] });
  try {
    const dmE = new EmbedBuilder().setTitle('⛏️ Minecraft Server Created!').setColor(0x57F287);
    dmE.addFields({ name: 'ID', value: `\`${sid}\``, inline: true }, { name: 'RAM', value: `\`${ram}\``, inline: true }, { name: 'CPU', value: `\`${cpu}\``, inline: true }, { name: 'Disk', value: `\`${disk}\``, inline: true }, { name: 'Expires', value: `<t:${Math.floor(exp.getTime() / 1000)}:R>` });
    await user.send({ embeds: [dmE] });
  } catch {}
});

register('minecraft', { sub: true }, async (msg, args) => {
  const sub = (args[0] || '').toLowerCase();
  if (sub === 'list') {
    if (!Object.keys(mc).length) return err(msg, 'No servers.');
    const e = makeEmbed('⛏️ All MC Servers');
    for (const [k, v] of Object.entries(mc).slice(0, 20)) e.addFields({ name: k, value: `<@${v.user}> • ${v.ram} • ${v.suspended ? '🛑' : '🟢'}` });
    return msg.reply({ embeds: [e] });
  }
  if (sub === 'manage') {
    const sid = args[1];
    if (!sid) {
      const mine = Object.keys(mc).filter(k => mc[k].user === msg.author.id);
      if (!mine.length) return err(msg, 'No servers.');
      return msg.reply({ embeds: [makeEmbed('⛏️ Your Servers', mine.map(s => `\`${s}\``).join('\n'))] });
    }
    const v = mc[sid];
    if (!v) return err(msg, 'Not found.');
    const e = makeEmbed(`⛏️ \`${sid}\``);
    e.addFields({ name: 'RAM', value: v.ram, inline: true }, { name: 'CPU', value: v.cpu, inline: true }, { name: 'Disk', value: v.disk, inline: true }, { name: 'State', value: v.suspended ? '🛑 Suspended' : '🟢 Active', inline: true });
    return msg.reply({ embeds: [e] });
  }
  if (sub === 'delete') {
    if (!isAdmin(msg) && !isOwner(msg)) return err(msg, 'Admin only.');
    if (!mc[args[1]]) return err(msg, 'Not found.');
    delete mc[args[1]]; save('minecraft', mc);
    return ok(msg, `Deleted \`${args[1]}\`.`);
  }
  if (sub === 'suspension') {
    if (!isAdmin(msg) && !isOwner(msg)) return err(msg, 'Admin only.');
    if (!mc[args[1]]) return err(msg, 'Not found.');
    mc[args[1]].suspended = !mc[args[1]].suspended; save('minecraft', mc);
    return ok(msg, `\`${args[1]}\` → **${mc[args[1]].suspended ? 'SUSPENDED' : 'ACTIVE'}**`);
  }
  if (sub === 'status') {
    const v = mc[args[1]];
    if (!v) return err(msg, 'Not found.');
    return msg.reply({ embeds: [makeEmbed(`⛏️ \`${args[1]}\``, `Owner: <@${v.user}>\nState: ${v.suspended ? '🛑' : '🟢'}`)] });
  }
});

register('gstart', { admin: true }, async (msg, args) => {
  const sec = parseTime(args[0]);
  const winners = parseInt(args[1]) || 1;
  const prize = args.slice(2).join(' ');
  if (!sec || !prize) return err(msg, `Usage: \`${PREFIX}gstart <time> <winners> <prize>\``);
  const ends = new Date(Date.now() + sec * 1000);
  const e = makeEmbed('🎁 GIVEAWAY', `**Prize:** ${prize}\n**Winners:** ${winners}\n**Ends:** <t:${Math.floor(ends.getTime() / 1000)}:R>\n\nReact with 🎉!`, COLOR.gold);
  const m = await msg.channel.send({ embeds: [e] });
  await m.react('🎉');
  giveaways[m.id] = { channel: m.channel.id, guild: msg.guild.id, prize, winners, ends: ends.toISOString(), ended: false };
  save('giveaways', giveaways);
});
register('gend', { admin: true }, async (msg, args) => {
  const g = giveaways[args[0]];
  if (!g || g.ended) return err(msg, 'Not found/ended.');
  g.ended = true; save('giveaways', giveaways);
  await endGiveaway(args[0]);
});
register('greroll', { admin: true }, async (msg, args) => {
  const g = giveaways[args[0]];
  if (!g) return err(msg, 'Not found.');
  const ch = client.channels.cache.get(g.channel);
  if (!ch) return err(msg, 'Channel missing.');
  try {
    const m = await ch.messages.fetch(args[0]);
    const users = [...(m.reactions.cache.get('🎉')?.users.cache.values() || [])].filter(u => !u.bot);
    if (!users.length) return err(msg, 'No entries.');
    await msg.channel.send(`🎉 Reroll: ${users[rand(0, users.length - 1)]}!`);
  } catch (e) { return err(msg, e.message); }
});
register('glist', { public: true }, async (msg) => {
  const active = Object.entries(giveaways).filter(([, g]) => !g.ended && g.guild === msg.guild.id);
  if (!active.length) return err(msg, 'No active.');
  const e = makeEmbed('🎁 Active');
  for (const [k, v] of active) e.addFields({ name: v.prize, value: `ID: \`${k}\`` });
  return msg.reply({ embeds: [e] });
});

async function endGiveaway(msgId) {
  const g = giveaways[msgId];
  if (!g) return;
  const ch = client.channels.cache.get(g.channel);
  if (!ch) return;
  try {
    const m = await ch.messages.fetch(msgId);
    const users = [...(m.reactions.cache.get('🎉')?.users.cache.values() || [])].filter(u => !u.bot);
    if (!users.length) return ch.send({ embeds: [makeEmbed('🎁 Ended', `No entries for **${g.prize}**.`, COLOR.warn)] });
    const n = Math.min(g.winners, users.length);
    const winners = users.sort(() => Math.random() - 0.5).slice(0, n);
    const e = makeEmbed('🎁 Ended', `**Prize:** ${g.prize}\n**Winners:** ${winners.map(w => w.toString()).join(' ')}`, COLOR.gold);
    await ch.send({ embeds: [e] });
    for (const w of winners) try { await w.send(`🎉 You won **${g.prize}**!`); } catch {}
  } catch {}
}

register('review', { public: true }, async (msg, args) => {
  const rating = parseInt(args[0]);
  if (!rating || rating < 1 || rating > 5) return err(msg, `**Usage:** \`${PREFIX}review <1-5> [comment]\``);
  const comment = args.slice(1).join(' ') || 'No comment provided';
  const gid = msg.guild.id;
  const cfg = reviewCfg[gid] || {};

  if (!reviews[gid]) reviews[gid] = [];
  const existing = reviews[gid].find(r => r.user === msg.author.id);
  if (existing) { existing.rating = rating; existing.comment = comment; existing.time = new Date().toISOString(); }
  else reviews[gid].push({ id: `REV-${rand(10000, 99999)}`, user: msg.author.id, rating, comment, time: new Date().toISOString() });
  save('reviews', reviews);

  const stars = '⭐'.repeat(rating) + '☆'.repeat(5 - rating);
  const avg = (reviews[gid].reduce((s, r) => s + r.rating, 0) / reviews[gid].length).toFixed(2);
  const rColor = rating >= 4 ? COLOR.ok : rating >= 3 ? COLOR.warn : COLOR.err;

  if (cfg.channel) {
    const ch = msg.guild.channels.cache.get(cfg.channel);
    if (ch) {
      const e = new EmbedBuilder().setColor(rColor)
        .setAuthor({ name: msg.author.username + ' left a review!', iconURL: msg.author.displayAvatarURL() })
        .setTitle('🌟  ═══  NEW REVIEW  ═══  🌟').setDescription(`>>> ${comment}`)
        .addFields({ name: '⭐ Rating', value: `${stars}\n**${rating}/5**`, inline: true }, { name: '👤 Reviewer', value: `${msg.author}`, inline: true }, { name: '📊 Average', value: `**${avg}/5** (${reviews[gid].length})`, inline: true })
        .setThumbnail(msg.author.displayAvatarURL({ size: 256 }))
        .setFooter({ text: FOOTER, iconURL: client.user?.displayAvatarURL() });
      await ch.send({ embeds: [e] });
    }
  }

  const okE = new EmbedBuilder().setColor(COLOR.ok).setTitle('✅  Review Submitted')
    .setDescription(`Thanks for your feedback! ✨\n\n${stars}\n**Your Rating:** \`${rating}/5\``)
    .addFields({ name: '📊 Average', value: `**${avg}/5**`, inline: true }, { name: '📝 Total', value: `**${reviews[gid].length}**`, inline: true }, { name: '✨ Status', value: existing ? '🔄 Updated' : '🆕 Added', inline: true });
  return msg.reply({ embeds: [okE] });
});
register('review-setup', { admin: true }, async (msg, args) => {
  const ch = msg.mentions.channels.first() || msg.guild.channels.cache.get(args[0]);
  if (!ch) return err(msg, `**Usage:** \`${PREFIX}review-setup <#channel>\``);
  if (!reviewCfg[msg.guild.id]) reviewCfg[msg.guild.id] = {};
  reviewCfg[msg.guild.id].channel = ch.id; save('review_cfg', reviewCfg);
  return ok(msg, `Review channel set to ${ch}.`);
});
register('review-stats', { public: true }, async (msg) => {
  const gid = msg.guild.id;
  const list = reviews[gid] || [];
  if (!list.length) return err(msg, 'No reviews yet.');
  const avg = (list.reduce((s, r) => s + r.rating, 0) / list.length).toFixed(2);
  const counts = [0, 0, 0, 0, 0];
  list.forEach(r => counts[r.rating - 1]++);
  const bar = (n, t) => { const p = t ? Math.round((n / t) * 20) : 0; return '█'.repeat(p) + '░'.repeat(20 - p); };
  const stars = '⭐'.repeat(Math.round(avg)) + '☆'.repeat(5 - Math.round(avg));
  const e = new EmbedBuilder().setColor(COLOR.gold).setTitle(`📊  Review Stats — ${msg.guild.name}`).setDescription(`### ${stars}\n**Average:** \`${avg}/5\`\n**Total:** \`${list.length}\``)
    .addFields(
      { name: '5 ⭐', value: `\`${bar(counts[4], list.length)}\` **${counts[4]}**` },
      { name: '4 ⭐', value: `\`${bar(counts[3], list.length)}\` **${counts[3]}**` },
      { name: '3 ⭐', value: `\`${bar(counts[2], list.length)}\` **${counts[2]}**` },
      { name: '2 ⭐', value: `\`${bar(counts[1], list.length)}\` **${counts[1]}**` },
      { name: '1 ⭐', value: `\`${bar(counts[0], list.length)}\` **${counts[0]}**` }
    );
  return msg.reply({ embeds: [e] });
});
register('review-list', { public: true }, async (msg) => {
  const list = reviews[msg.guild.id] || [];
  if (!list.length) return err(msg, 'No reviews yet.');
  const sorted = [...list].sort((a, b) => new Date(b.time) - new Date(a.time));
  const e = makeEmbed(`📝 Recent Reviews — ${msg.guild.name}`);
  for (const r of sorted.slice(0, 10)) {
    const stars = '⭐'.repeat(r.rating) + '☆'.repeat(5 - r.rating);
    e.addFields({ name: `${stars} • ${r.id}`, value: `> ${r.comment.slice(0, 180)}\n— <@${r.user}>` });
  }
  return msg.reply({ embeds: [e] });
});

const isPremiumUid = (uid) => {
  const d = premiumData[uid];
  if (!d) return false;
  try { return new Date(d.expires) > new Date(); } catch { return false; }
};
register('premium', { sub: true }, async (msg, args) => {
  const sub = (args[0] || '').toLowerCase();
  if (!sub) return msg.reply({ embeds: [makeEmbed('💎 Premium', `\`${PREFIX}premium add <@u> <days>\`\n\`${PREFIX}premium remove <@u>\`\n\`${PREFIX}premium check <@u>\``, COLOR.premium)] });
  if (sub === 'add') {
    if (!isAdmin(msg) && !isOwner(msg)) return err(msg, 'Admin only.');
    const u = msg.mentions.users.first();
    const days = parseInt(args[2]);
    if (!u || !days) return err(msg, `Usage: \`${PREFIX}premium add <@user> <days>\``);
    const exp = new Date(Date.now() + days * 86400000);
    premiumData[u.id] = { expires: exp.toISOString(), added: new Date().toISOString() };
    save('premium', premiumData);
    return msg.channel.send({ embeds: [makeEmbed('💎 Premium Granted', `${u} until <t:${Math.floor(exp.getTime() / 1000)}:R>`, COLOR.premium)] });
  }
  if (sub === 'remove') {
    if (!isAdmin(msg) && !isOwner(msg)) return err(msg, 'Admin only.');
    const u = msg.mentions.users.first();
    if (!u) return err(msg, 'Mention a user.');
    delete premiumData[u.id]; save('premium', premiumData);
    return ok(msg, `Removed premium from ${u}.`);
  }
  if (sub === 'check') {
    const u = msg.mentions.users.first() || msg.author;
    if (!isPremiumUid(u.id)) return err(msg, `${u} is not premium.`);
    const exp = new Date(premiumData[u.id].expires);
    return msg.reply({ embeds: [makeEmbed('💎 Premium Active', `Expires: <t:${Math.floor(exp.getTime() / 1000)}:R>`, COLOR.premium)] });
  }
});

register('auto-roll', { admin: true }, async (msg) => {
  const role = msg.mentions.roles.first();
  if (!role) return err(msg, 'Mention a role.');
  const ar = load('autoroles', {}); ar[msg.guild.id] = role.id; save('autoroles', ar);
  return ok(msg, `Auto-role set to ${role}.`);
});
register('auto-roll_remove', { admin: true }, async (msg) => {
  const ar = load('autoroles', {}); delete ar[msg.guild.id]; save('autoroles', ar);
  return ok(msg, 'Auto-role removed.');
});

register('owner', { owner: true, sub: true }, async (msg, args) => {
  const sub = (args[0] || '').toLowerCase();
  if (!sub) return msg.reply({ embeds: [makeEmbed('👑 Owner', `\`${PREFIX}owner status\` • \`${PREFIX}owner maintenance <on/off>\``, COLOR.gold)] });
  if (sub === 'status') {
    const e = makeEmbed('👑 Bot Status', null, COLOR.gold);
    e.addFields(
      { name: 'User', value: String(client.user) },
      { name: 'Guilds', value: String(client.guilds.cache.size), inline: true },
      { name: 'Members', value: String(client.guilds.cache.reduce((a, g) => a + g.memberCount, 0)), inline: true },
      { name: 'Latency', value: `${Math.round(client.ws.ping)}ms`, inline: true },
      { name: 'Maintenance', value: MAINT ? '🛠️ ON' : '🟢 OFF', inline: true },
      { name: 'QR File', value: fs.existsSync(QR_PATH) ? '✅ Found' : '❌ Missing', inline: true },
      { name: 'AI Screenshot Verify', value: AI_SCREENSHOT_VERIFY ? '✅ On' : '❌ Off', inline: true },
      { name: 'Owner IDs', value: OWNER_IDS.length ? OWNER_IDS.map(id => `\`${id}\``).join('\n') : '⚠️ None', inline: false }
    );
    return msg.reply({ embeds: [e] });
  }
  if (sub === 'maintenance') {
    MAINT = ['on', 'true', 'yes', '1'].includes((args[1] || '').toLowerCase());
    return ok(msg, `Maintenance **${MAINT ? 'ON' : 'OFF'}**`);
  }
});

// ═══ MESSAGE HANDLER ═══
client.on('messageCreate', async (msg) => {
  try {
    if (msg.author.bot) return;

    // ═══ DM ═══
    if (!msg.guild) {
      if (pendingProofUpload.has(msg.author.id)) {
        const pid = pendingProofUpload.get(msg.author.id);
        const f = findPayment(pid);
        if (!f || f.rec.status !== 'pending') { pendingProofUpload.delete(msg.author.id); return; }

        let imageUrl = null, imageName = null;
        if (msg.attachments.size) {
          const att = msg.attachments.first();
          imageUrl = att.url; imageName = att.name;
        } else if (msg.content.trim().startsWith('http')) {
          imageUrl = msg.content.trim(); imageName = 'screenshot.png';
        }
        if (!imageUrl) return msg.reply({ embeds: [makeEmbed('❌ No Image', 'Please attach your payment screenshot as an image file.', COLOR.err)] });

        const verifying = await msg.reply({ embeds: [makeEmbed('🔍 Verifying Screenshot…', '⏳ AI is analyzing your payment screenshot. Please wait…', COLOR.info)] });

        let imgBuf = null;
        try { imgBuf = await fetchImageBuffer(imageUrl); } catch (e) { console.log('imgBuf fetch fail:', e.message); }

        let verdict = { verdict: 'unclear', notes: 'AI verification not available' };
        if (AI_SCREENSHOT_VERIFY && imgBuf) {
          try { verdict = await aiVerifyScreenshot(imgBuf, f.rec.amount, f.rec.method, f.rec.product); }
          catch (e) { console.log('AI verify fail:', e.message); }
        }
        console.log('[AI Verdict]', JSON.stringify(verdict));

        f.rec.status = 'claimed';
        f.rec.proof_url = imageUrl;
        f.rec.proof_name = imageName;
        f.rec.claimed_at = new Date().toISOString();
        f.rec.claimed_by = msg.author.id;
        f.rec.ai_verdict = verdict;
        save('payments', payments);
        pendingProofUpload.delete(msg.author.id);
        await verifying.delete().catch(() => {});

        const confirmE = makeEmbed('✅ Screenshot Received', null, COLOR.ok);
        confirmE.setDescription(
          `Thank you! Your payment proof has been submitted.\n\n` +
          `📋 **Payment ID:** \`${pid}\`\n` +
          `🤖 **AI Verdict:** ${getVerdictEmoji(verdict.verdict)} ${getVerdictText(verdict.verdict)}\n` +
          `⏳ **Status:** Pending admin verification\n\n` +
          `You will be notified once an admin reviews your payment. Please be patient. 🙏`
        );
        await msg.reply({ embeds: [confirmE] });

        // OWNER DM
        try {
          const owner = await client.users.fetch(String(OWNER_ID));
          const ownerE = makeEmbed('🔔 New Payment Verification Needed', null, COLOR.warn);
          ownerE.setDescription('A new payment proof has been submitted.\n\n**Please verify and Approve or Reject.**');
          ownerE.addFields(
            { name: '📋 Payment ID', value: `\`${pid}\``, inline: true },
            { name: '💰 Amount', value: `${PAY_SYM}${f.rec.amount}`, inline: true },
            { name: '💳 Method', value: (f.rec.method || '—').toUpperCase(), inline: true },
            { name: '📦 Product', value: f.rec.product || '—' },
            { name: '👤 Payer', value: `<@${f.rec.from}> (\`${f.rec.from}\`)`, inline: true },
            { name: '🎯 Receiver', value: `<@${f.rec.to}> (\`${f.rec.to}\`)`, inline: true }
          );
          const vColor = getVerdictColor(verdict.verdict);
          const vEmoji = getVerdictEmoji(verdict.verdict);
          const vText = getVerdictText(verdict.verdict);
          let aiText = `${vEmoji} **${vText}**`;
          if (verdict.confidence) aiText += ` • Confidence: \`${verdict.confidence}\``;
          if (verdict.is_payment_screenshot !== undefined) aiText += `\n📸 Payment screenshot: \`${verdict.is_payment_screenshot ? 'yes' : 'no'}\``;
          if (verdict.amount_visible !== undefined) aiText += `\n💵 Amount visible: \`${verdict.amount_visible ? 'yes' : 'no'}\``;
          if (verdict.amount_matches !== undefined) aiText += `\n🎯 Amount matches: \`${verdict.amount_matches ? 'yes' : 'no'}\``;
          if (verdict.payment_success_indicated !== undefined) aiText += `\n✅ Success shown: \`${verdict.payment_success_indicated ? 'yes' : 'no'}\``;
          if (verdict.notes) aiText += `\n📝 ${verdict.notes}`;
          ownerE.addFields({ name: '🤖 AI Analysis', value: aiText.slice(0, 1000) });
          ownerE.addFields(
            { name: '🏠 Server', value: `${client.guilds.cache.get(String(f.rec.guild))?.name || 'Unknown'}` },
            { name: '⏰ Submitted', value: `<t:${Math.floor(Date.now() / 1000)}:R>` }
          );
          ownerE.setColor(vColor);

          const row = new ActionRowBuilder().addComponents(
            new ButtonBuilder().setCustomId(`owner_approve_${pid}`).setLabel('✅ Approve').setStyle(ButtonStyle.Success),
            new ButtonBuilder().setCustomId(`owner_reject_${pid}`).setLabel('❌ Reject').setStyle(ButtonStyle.Danger)
          );

          let sent = false;
          if (imgBuf) {
            try {
              let ext = 'png';
              if (imageName && imageName.includes('.')) ext = imageName.split('.').pop().toLowerCase();
              else if (imageUrl.match(/\.jpe?g/i)) ext = 'jpg';
              else if (imageUrl.match(/\.gif/i)) ext = 'gif';
              else if (imageUrl.match(/\.webp/i)) ext = 'webp';
              const fname = `payment-proof.${ext}`;
              const attachment = new AttachmentBuilder(imgBuf, { name: fname });
              ownerE.setImage(`attachment://${fname}`);
              await owner.send({ embeds: [ownerE], components: [row], files: [attachment] });
              sent = true;
            } catch (attErr) { console.log('Attach fail:', attErr.message); }
          }
          if (!sent) {
            ownerE.setImage(imageUrl);
            try { await owner.send({ embeds: [ownerE], components: [row] }); sent = true; }
            catch (urlErr) { console.log('URL embed fail:', urlErr.message); }
          }
          console.log(sent ? `✅ Owner DM sent for ${pid}` : `❌ Owner DM failed for ${pid}`);
        } catch (e) {
          console.log('Owner DM fail:', e.message);
          const logId = payCfg[f.rec.guild]?.log_channel;
          if (logId) {
            const guild = client.guilds.cache.get(String(f.rec.guild));
            const ch = guild?.channels.cache.get(logId);
            if (ch) {
              const fallbackE = makeEmbed('🔔 Payment Proof (Owner DM failed)', null, COLOR.warn);
              fallbackE.addFields(
                { name: 'ID', value: `\`${pid}\``, inline: true },
                { name: 'Amount', value: `${PAY_SYM}${f.rec.amount}`, inline: true },
                { name: 'Payer', value: `<@${f.rec.from}>`, inline: true },
                { name: '🤖 AI Verdict', value: `${getVerdictEmoji(verdict.verdict)} ${getVerdictText(verdict.verdict)}` }
              );
              fallbackE.setImage(imageUrl);
              const row = new ActionRowBuilder().addComponents(
                new ButtonBuilder().setCustomId(`owner_approve_${pid}`).setLabel('✅ Approve').setStyle(ButtonStyle.Success),
                new ButtonBuilder().setCustomId(`owner_reject_${pid}`).setLabel('❌ Reject').setStyle(ButtonStyle.Danger)
              );
              ch.send({ embeds: [fallbackE], components: [row] }).catch(() => {});
            }
          }
        }
        return;
      }
      return;
    }

    // ═══ GUILD ═══
    if (MAINT && !OWNER_IDS.includes(msg.author.id)) return;

    if (AI_PING && client.user && msg.mentions.has(client.user) && !msg.content.startsWith(PREFIX)) {
      const prompt = msg.content.replace(new RegExp(`<@!?${client.user.id}>`, 'g'), '').trim() || 'hello';
      const thinking = await msg.reply({ embeds: [makeEmbed('🤖 Thinking…', '⏳ Please wait…', COLOR.info)] });
      let ans;
      try { ans = await aiAsk(prompt, msg.author.id); }
      catch (e) { ans = '❌ AI error.'; }
      await thinking.edit({ content: ans.slice(0, 1990) || '…', embeds: [] }).catch(() => {});
      return;
    }

    const protCfg = load('protection', {})[msg.guild.id];
    if (protCfg?.enabled && !protCfg.whitelist.includes(msg.author.id)) {
      if (protCfg.anti_invite && /(discord\.gg|discord\.com\/invite)\/\w+/i.test(msg.content)) {
        try { await msg.delete(); } catch {} return;
      }
      if (protCfg.anti_link && /https?:\/\//i.test(msg.content)) {
        try { await msg.delete(); } catch {} return;
      }
      if (protCfg.anti_spam) {
        const key = `${msg.guild.id}-${msg.author.id}`;
        const now = Date.now();
        const bucket = (spamCache.get(key) || []).filter(t => now - t < 5000);
        bucket.push(now);
        spamCache.set(key, bucket);
        if (bucket.length > 5) {
          try { await msg.member.timeout(5 * 60 * 1000, 'Anti-spam'); } catch {}
          return;
        }
      }
    }

    if (!msg.content.startsWith(PREFIX)) return;
    const args = msg.content.slice(PREFIX.length).trim().split(/\s+/);
    const name = args.shift().toLowerCase();
    const command = client.commands.get(name);
    if (!command) return;

    const allowed = await checkPermission(msg, command.opts);
    if (!allowed) return;

    await command.handler(msg, args);
  } catch (e) {
    console.error('Message error:', e);
    try { await err(msg, `\`${e.message}\``); } catch {}
  }
});

client.on('guildMemberAdd', async (member) => {
  const arId = load('autoroles', {})[member.guild.id];
  if (arId) { try { await member.roles.add(arId); } catch {} }
  const c = load('welcome', {})[member.guild.id];
  if (c?.channel) {
    const ch = member.guild.channels.cache.get(c.channel);
    if (ch) {
      const e = new EmbedBuilder().setColor(COLOR.main).setTimestamp(new Date())
        .setTitle((c.title || `Welcome ${member.user.username}!`).replace('{user}', member.user.username).replace('{guild}', member.guild.name))
        .setDescription((c.desc || `Hey ${member}, welcome to **${member.guild.name}**!`).replace('{user}', `${member}`).replace('{guild}', member.guild.name))
        .setThumbnail(member.user.displayAvatarURL());
      if (c.gif) e.setImage(c.gif);
      try { await ch.send({ content: `${member}`, embeds: [e] }); } catch {}
    }
  }
});

client.on('guildMemberRemove', async (member) => {
  const c = load('goodbye', {})[member.guild.id];
  if (c?.channel) {
    const ch = member.guild.channels.cache.get(c.channel);
    if (ch) {
      const e = new EmbedBuilder().setColor(COLOR.warn).setDescription(`👋 **${member.user.username}** left.`).setThumbnail(member.user.displayAvatarURL());
      try { await ch.send({ embeds: [e] }); } catch {}
    }
  }
});

setInterval(async () => {
  const data = load('minecraft', {});
  const now = new Date();
  for (const k in data) {
    const v = data[k];
    try {
      if (new Date(v.expires) < now && !v.suspended) {
        v.suspended = true;
        try { const u = await client.users.fetch(String(v.user)); await u.send({ embeds: [makeEmbed('⚠️ Server Expired', `\`${k}\` suspended.`, COLOR.warn)] }); } catch {}
      }
    } catch {}
  }
  save('minecraft', data);
}, 30 * 60 * 1000);

const FESTIVALS = {
  '01-01': ['🎉 Happy New Year!', 'Wishing everyone a fantastic New Year!'],
  '01-26': ['🇮🇳 Republic Day', 'Happy Republic Day!'],
  '03-08': ['🌸 Holi', 'Happy Holi!'],
  '08-15': ['🇮🇳 Independence Day', 'Happy Independence Day!'],
  '10-31': ['🎃 Halloween', 'Spooky season!'],
  '11-14': ['🪔 Diwali', 'Happy Diwali!'],
  '12-25': ['🎄 Merry Christmas', 'Merry Christmas!']
};

setInterval(async () => {
  if (!FEST_CH || !AUTO_FEST) return;
  const key = new Date().toISOString().slice(5, 10);
  const [title, desc] = FESTIVALS[key] || [];
  if (!title) return;
  const ch = client.channels.cache.get(String(FEST_CH));
  if (ch) try { await ch.send({ content: '@everyone', embeds: [makeEmbed(title, desc, COLOR.gold)] }); } catch {}
}, 6 * 60 * 60 * 1000);

client.once('ready', async () => {
  console.log('╔═══════════════════════════════════════════╗');
  console.log(`║  ${BOT_NAME} v8.1 — ONLINE`);
  console.log(`║  User    : ${client.user.tag}`);
  console.log(`║  Guilds  : ${client.guilds.cache.size}`);
  console.log(`║  Prefix  : ${PREFIX}`);
  console.log(`║  Raw OWNER_ID : "${OWNER_IDS_RAW}"`);
  console.log(`║  Parsed Owners: ${OWNER_IDS.length ? OWNER_IDS.join(', ') : '⚠️  NONE'}`);
  console.log(`║  QR      : ${fs.existsSync(QR_PATH) ? '✅ Local (qr.png)' : '⚠️  Not found'}`);
  console.log(`║  AI Vfy  : ${AI_SCREENSHOT_VERIFY ? '✅ Enabled' : '❌ Disabled'}`);
  console.log('╚═══════════════════════════════════════════╝');
  if (!OWNER_IDS.length) {
    console.log('⚠️  WARNING: No valid OWNER_ID loaded!');
    console.log('   Fix .env: OWNER_ID=<your_discord_id>');
    console.log('   Get your ID: !whoami command in Discord');
  }
  try {
    client.user.setPresence({
      activities: [{ name: `${PREFIX}help | ${BOT_NAME}`, type: ActivityType.Watching }],
      status: 'online'
    });
  } catch {}
  console.log('✅ Bot ready!');
});

client.on('error', (e) => console.error('Client error:', e.message));
process.on('unhandledRejection', (e) => console.error('Unhandled:', e?.message || e));

if (!TOKEN) {
  console.error('❌ DISCORD_TOKEN missing in .env');
  process.exit(1);
}

client.login(TOKEN);