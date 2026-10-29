/* Portable, local-only conversation backup format. Browser + Node.js compatible. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.ConversationBackup = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const FORMAT = "mon-ia-conversations";
  const VERSION = 1;
  const MAX_CONVERSATIONS = 200;
  const MAX_MESSAGES = 1000;
  const MAX_CONTENT_CHARS = 2000000;

  function isRecord(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function normalize(list) {
    if (!Array.isArray(list) || list.length > MAX_CONVERSATIONS) {
      throw new Error("Nombre de conversations non valide (maximum 200).");
    }
    let totalLength = 0;
    const out = list.map(function (item) {
      if (!isRecord(item) || typeof item.title !== "string" ||
          item.title.length > 120 || !["fast", "agent"].includes(item.mode) ||
          !Array.isArray(item.messages) || item.messages.length > MAX_MESSAGES) {
        throw new Error("Conversation de sauvegarde invalide.");
      }
      const messages = item.messages.map(function (message) {
        if (!isRecord(message) || !["user", "assistant"].includes(message.role) ||
            typeof message.content !== "string" || message.content.length > 100000) {
          throw new Error("Message de sauvegarde invalide.");
        }
        totalLength += message.content.length;
        if (totalLength > MAX_CONTENT_CHARS) {
          throw new Error("Sauvegarde trop volumineuse.");
        }
        return {role: message.role, content: message.content};
      });
      return {title: item.title || "Conversation", mode: item.mode, messages: messages};
    });
    return out;
  }

  function createExport(conversations, date) {
    const sanitized = normalize(conversations);
    if (!sanitized.length) throw new Error("Aucune conversation à exporter.");
    return {
      kind: FORMAT,
      version: VERSION,
      created_at: date || new Date().toISOString(),
      conversations: sanitized
    };
  }

  function parseBackup(text) {
    if (typeof text !== "string" || text.length > 5000000) {
      throw new Error("Fichier JSON trop volumineux ou invalide.");
    }
    let data;
    try { data = JSON.parse(text); }
    catch (error) { throw new Error("Le fichier n'est pas un JSON valide."); }
    if (!isRecord(data) || data.kind !== FORMAT || data.version !== VERSION) {
      throw new Error("Ce fichier n'est pas une sauvegarde Mon IA v1.");
    }
    const conversations = normalize(data.conversations);
    if (!conversations.length) throw new Error("Aucune conversation dans le fichier.");
    return conversations;
  }

  function mergeImported(current, imported, newId, newSession) {
    if (!Array.isArray(current) || typeof newId !== "function" ||
        typeof newSession !== "function") {
      throw new Error("État des conversations invalide.");
    }
    const clean = normalize(imported);
    if (current.length + clean.length > MAX_CONVERSATIONS) {
      throw new Error("Limite de 200 conversations : supprimez des archives avant import.");
    }
    const existingIds = new Set(current.map(function (c) { return c.id; }));
    const received = new Set();
    const renamed = clean.map(function (c) {
      const id = newId();
      const session = newSession();
      if (typeof id !== "string" || !id || existingIds.has(id) || received.has(id) ||
          typeof session !== "string" || !/^mobile-[a-zA-Z0-9_-]{1,50}$/.test(session)) {
        throw new Error("Identifiant de restauration invalide ou en doublon.");
      }
      received.add(id);
      // Never reuse a server-side OpenClaw session from a different device.
      return {id: id, title: c.title, mode: c.mode, session: session, messages: c.messages};
    });
    return renamed.concat(current);
  }

  return {createExport: createExport, parseBackup: parseBackup,
          mergeImported: mergeImported, normalize: normalize};
});
