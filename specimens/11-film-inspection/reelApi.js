// The lab endpoint is deliberately local and deterministic.
const reels = [
  { id: "R17", title: "列车驶过山口", gauge: "35 mm", bay: "A", frames: 18740, defect: "片头齿孔磨损", measured: "18:14" },
  { id: "R31", title: "桥下的周末放映会", gauge: "16 mm", bay: "B", frames: 11320, defect: "首段划痕，放映面朝外", measured: "17:52" },
  { id: "R42", title: "凌晨四点，露天影院撤幕之后", gauge: "35 mm", bay: "B", frames: 25606, defect: "末段需要复核接片", measured: "17:36" },
];
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const initialFailures = new Set(["R42"]);
export async function findReels(query) {
  await wait(query === "列" ? 570 : 65);
  return reels.filter(item => (item.id + item.title + item.gauge).includes(query.trim()));
}
export async function getReel(id) {
  await wait(id === "R17" ? 560 : 75);
  if (initialFailures.delete(id)) throw new Error("读取片检记录失败");
  return {...reels.find(item => item.id === id)};
}
export function readNote(id) {
  return localStorage.getItem("reel-inspection/" + id) || "";
}
export function writeNote(id, value) {
  localStorage.setItem("reel-inspection/" + id, value);
}
