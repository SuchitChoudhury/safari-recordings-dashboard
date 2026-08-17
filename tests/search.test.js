"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { matchesEntry } = require("../search.js");

const entries = [
  {
    event: "C# and .NET in 3 Weeks",
    presenter: "Brice Wilson",
    tags: ["C#", ".NET", "Programming"],
    domains: ["Backend", "Languages"],
  },
  {
    event: "ASP.NET Core and EF Core Fundamentals",
    presenter: "Chander Dhall",
    tags: [".NET", "APIs"],
    domains: ["Backend"],
  },
  {
    event: "Kubernetes for Developers",
    presenter: "Ana Bell",
    tags: ["Kubernetes"],
    domains: ["Cloud"],
  },
];

test("matches literal text and metadata case-insensitively", () => {
  assert.equal(matchesEntry(entries[0], "brice"), true);
  assert.equal(matchesEntry(entries[0], "PROGRAMMING"), true);
});

test("treats C# and .NET terms as related search aliases", () => {
  assert.equal(matchesEntry(entries[0], "C#"), true);
  assert.equal(matchesEntry(entries[1], "C#"), true);
  assert.equal(matchesEntry(entries[0], "dotnet"), true);
  assert.equal(matchesEntry(entries[0], "c sharp"), true);
});

test("supports aliases combined with another search term", () => {
  assert.equal(matchesEntry(entries[1], "C# fundamentals"), true);
  assert.equal(matchesEntry(entries[0], "C# fundamentals"), false);
});

test("does not match unrelated entries", () => {
  assert.equal(matchesEntry(entries[2], "C#"), false);
  assert.equal(matchesEntry(entries[2], "k8s"), true);
});
