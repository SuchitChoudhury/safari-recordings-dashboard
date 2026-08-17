"use strict";

(function initSearchLogic(root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.SearchLogic = api;
})(typeof globalThis !== "undefined" ? globalThis : this, () => {
  const ALIAS_GROUPS = [
    ["c#", "c sharp", ".net", "dotnet", "dot net", "asp.net"],
    ["c++", "cpp"],
    ["kubernetes", "k8s"],
    ["javascript", "js"],
    ["typescript", "ts"],
  ];

  const aliasMap = new Map();
  for (const group of ALIAS_GROUPS) {
    for (const alias of group) aliasMap.set(alias, group);
  }

  const normalize = value => String(value ?? "").trim().toLowerCase();

  function searchGroups(query) {
    const normalized = normalize(query);
    if (!normalized) return [];

    const exactAliases = aliasMap.get(normalized);
    if (exactAliases) return [exactAliases];

    const tokens = normalized.match(/[a-z0-9+#.]+/g) || [];
    return tokens.map(token => aliasMap.get(token) || [token]);
  }

  function matchesEntry(entry, query) {
    const groups = searchGroups(query);
    if (!groups.length) return true;

    const haystack = [
      entry.event,
      entry.presenter,
      ...(entry.tags || []),
      ...(entry.domains || []),
    ].map(normalize).join(" ");

    return groups.every(aliases => aliases.some(alias => haystack.includes(alias)));
  }

  return { matchesEntry, searchGroups };
});
