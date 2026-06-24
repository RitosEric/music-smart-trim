import {
  formatTime,
  formatFileSize,
  parseTimeString,
  formatStarRating,
} from "./formatters";

test("formatTime formats seconds to MM:SS", () => {
  expect(formatTime(0)).toBe("0:00");
  expect(formatTime(65)).toBe("1:05");
  expect(formatTime(125)).toBe("2:05");
  expect(formatTime(3661)).toBe("61:01");
});

test("formatFileSize formats bytes to human readable", () => {
  expect(formatFileSize(0)).toBe("0 B");
  expect(formatFileSize(1024)).toBe("1.00 KB");
  expect(formatFileSize(1048576)).toBe("1.00 MB");
});

test("parseTimeString parses MM:SS to seconds", () => {
  expect(parseTimeString("0:00")).toBe(0);
  expect(parseTimeString("1:30")).toBe(90);
  expect(parseTimeString("2:05")).toBe(125);
});

test("formatStarRating renders whole stars (rounded to nearest)", () => {
  expect(formatStarRating(0)).toBe("☆☆☆☆☆");
  expect(formatStarRating(2.4)).toBe("★★☆☆☆");
  expect(formatStarRating(2.5)).toBe("★★★☆☆"); // rounds up at half
  expect(formatStarRating(3.7)).toBe("★★★★☆");
  expect(formatStarRating(5)).toBe("★★★★★");
  expect(formatStarRating(undefined)).toBe("☆☆☆☆☆");
});
