// One signing flow at a time: a second tap while the first is waiting for approval or for the network is ignored.
export function createGate() {
  let busy = false;
  return { tryEnter() { if (busy) return false; busy = true; return true; }, leave() { busy = false; }, get busy() { return busy; } };
}
