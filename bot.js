require("dotenv").config();
const { Telegraf } = require("telegraf");

const bot = new Telegraf(process.env.TELEGRAM_BOT_TOKEN);

// In-memory store: chatId -> { text: string, messageId: number }
const stickyStore = new Map();

async function deleteOldSticky(chatId) {
  const sticky = stickyStore.get(chatId);
  if (!sticky) return;
  try {
    await bot.telegram.deleteMessage(chatId, sticky.messageId);
  } catch {
    // Message may already be deleted or too old (>48h)
  }
}

bot.command("setsticky", async (ctx) => {
  const text = ctx.message.text.replace(/^\/setsticky\s*/, "").trim();

  if (!text) {
    return ctx.reply("Usage: /setsticky <your message>");
  }

  const chatId = ctx.chat.id;
  await deleteOldSticky(chatId);

  const sent = await ctx.reply(`📌 ${text}`);
  stickyStore.set(chatId, { text, messageId: sent.message_id });

  try {
    await ctx.deleteMessage();
  } catch {
    // Bot may lack permission to delete in some chats
  }
});

bot.command("clearsticky", async (ctx) => {
  const chatId = ctx.chat.id;
  await deleteOldSticky(chatId);
  stickyStore.delete(chatId);
  await ctx.reply("Sticky message cleared.");
});

// Re-bump sticky on every message
bot.on("message", async (ctx) => {
  const chatId = ctx.chat.id;
  const sticky = stickyStore.get(chatId);
  if (!sticky) return;

  // Ignore the sticky message itself to avoid infinite loop
  if (ctx.message.message_id === sticky.messageId) return;

  await deleteOldSticky(chatId);

  // Use sendMessage (not reply) so it's a standalone message with no quote
  const sent = await bot.telegram.sendMessage(chatId, `📌 ${sticky.text}`);
  stickyStore.set(chatId, { text: sticky.text, messageId: sent.message_id });
});

bot.launch().then(() => console.log("Bot started."));

process.once("SIGINT", () => bot.stop("SIGINT"));
process.once("SIGTERM", () => bot.stop("SIGTERM"));
