import {
  loadRecents,
  upsertRecent,
  removeRecent,
  MAX_RECENT,
} from "./recentUploads";

beforeEach(() => {
  window.localStorage.clear();
});

const makeEntry = (id, extra = {}) => ({
  jobId: id,
  filename: `${id}.mp3`,
  originalLength: 120,
  coverFilename: null,
  uploadedAt: new Date(0).toISOString(),
  result: { outputs: [] },
  ...extra,
});

test("loadRecents returns [] when localStorage is empty", () => {
  expect(loadRecents()).toEqual([]);
});

test("loadRecents tolerates corrupt JSON", () => {
  window.localStorage.setItem("mst.recentUploads.v1", "not-json");
  expect(loadRecents()).toEqual([]);
});

test("upsertRecent prepends new entries", () => {
  upsertRecent(makeEntry("a"));
  const { recents } = upsertRecent(makeEntry("b"));
  expect(recents.map((r) => r.jobId)).toEqual(["b", "a"]);
});

test("upsertRecent replaces and bumps an existing jobId", () => {
  upsertRecent(makeEntry("a"));
  upsertRecent(makeEntry("b"));
  upsertRecent(makeEntry("c"));
  const { recents } = upsertRecent(makeEntry("a", { filename: "a-updated.mp3" }));
  expect(recents.map((r) => r.jobId)).toEqual(["a", "c", "b"]);
  expect(recents[0].filename).toBe("a-updated.mp3");
});

test("upsertRecent caps the list at MAX_RECENT and reports evictions", () => {
  for (let i = 0; i < MAX_RECENT; i++) upsertRecent(makeEntry(`old-${i}`));
  const { recents, evicted } = upsertRecent(makeEntry("new"));
  expect(recents).toHaveLength(MAX_RECENT);
  expect(recents[0].jobId).toBe("new");
  expect(evicted.map((r) => r.jobId)).toEqual(["old-0"]);
});

test("upsertRecent with missing jobId is a no-op", () => {
  upsertRecent(makeEntry("a"));
  const { recents, evicted } = upsertRecent({ filename: "x.mp3" });
  expect(recents.map((r) => r.jobId)).toEqual(["a"]);
  expect(evicted).toEqual([]);
});

test("removeRecent drops the matching entry", () => {
  upsertRecent(makeEntry("a"));
  upsertRecent(makeEntry("b"));
  const remaining = removeRecent("a");
  expect(remaining.map((r) => r.jobId)).toEqual(["b"]);
  expect(loadRecents().map((r) => r.jobId)).toEqual(["b"]);
});
