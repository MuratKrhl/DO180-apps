/**
 * Layout Configuration
 */

;(() => {
  // Set default layout attributes
  function setLayoutAttributes() {
    const html = document.documentElement

    // Set default attributes if not present
    if (!html.getAttribute("data-layout")) {
      html.setAttribute("data-layout", "vertical")
    }
    if (!html.getAttribute("data-topbar")) {
      html.setAttribute("data-topbar", "light")
    }
    if (!html.getAttribute("data-sidebar")) {
      html.setAttribute("data-sidebar", "dark")
    }
    if (!html.getAttribute("data-sidebar-size")) {
      html.setAttribute("data-sidebar-size", "lg")
    }
  }

  // Initialize layout on page load
  document.addEventListener("DOMContentLoaded", setLayoutAttributes)
})()
