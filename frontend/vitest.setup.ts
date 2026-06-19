import "@testing-library/jest-dom/vitest";

// jsdom no implementa estas APIs de puntero/scroll que usan los primitivos de
// Radix (dropdown-menu, select). Sin ellas, abrir un menú lanza una excepción.
if (typeof Element !== "undefined") {
  Element.prototype.hasPointerCapture ??= () => false;
  Element.prototype.setPointerCapture ??= () => {};
  Element.prototype.releasePointerCapture ??= () => {};
  Element.prototype.scrollIntoView ??= () => {};
}

// Radix Popper (dropdown-menu, select) usa ResizeObserver, ausente en jsdom.
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
