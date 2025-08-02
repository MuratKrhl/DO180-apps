/**
 * Middleware Portal - Main Application JavaScript
 */

;(() => {
  // Initialize when DOM is ready
  document.addEventListener("DOMContentLoaded", () => {
    initializeApp()
  })

  function initializeApp() {
    initializeSidebar()
    initializeSearch()
    initializeTooltips()
    initializeAlerts()
  }

  // Sidebar functionality
  function initializeSidebar() {
    const hamburgerBtn = document.getElementById("topnav-hamburger-icon")
    const sidebar = document.querySelector(".app-menu")
    const overlay = document.querySelector(".vertical-overlay")
    const mainContent = document.querySelector(".main-content")

    if (hamburgerBtn) {
      hamburgerBtn.addEventListener("click", () => {
        document.body.classList.toggle("sidebar-enable")

        if (window.innerWidth <= 991) {
          sidebar.classList.toggle("show")
          overlay.classList.toggle("show")
        }
      })
    }

    // Close sidebar on overlay click (mobile)
    if (overlay) {
      overlay.addEventListener("click", () => {
        document.body.classList.remove("sidebar-enable")
        sidebar.classList.remove("show")
        overlay.classList.remove("show")
      })
    }

    // Handle sidebar collapse/expand
    const verticalHover = document.getElementById("vertical-hover")
    if (verticalHover) {
      verticalHover.addEventListener("click", () => {
        document.body.classList.toggle("sidebar-collapsed")
      })
    }
  }

  // Search functionality
  function initializeSearch() {
    const searchInput = document.getElementById("search-options")
    const searchClose = document.getElementById("search-close-options")

    if (searchInput) {
      searchInput.addEventListener("input", function () {
        if (this.value.length > 0) {
          searchClose.classList.remove("d-none")
        } else {
          searchClose.classList.add("d-none")
        }
      })
    }

    if (searchClose) {
      searchClose.addEventListener("click", function () {
        searchInput.value = ""
        this.classList.add("d-none")
        searchInput.focus()
      })
    }
  }

  // Initialize Bootstrap tooltips
  function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    const bootstrap = window.bootstrap // Declare the bootstrap variable
    tooltipTriggerList.map((tooltipTriggerEl) => new bootstrap.Tooltip(tooltipTriggerEl))
  }

  // Auto-hide alerts
  function initializeAlerts() {
    const alerts = document.querySelectorAll(".alert")
    alerts.forEach((alert) => {
      if (alert.classList.contains("alert-success")) {
        setTimeout(() => {
          alert.style.opacity = "0"
          setTimeout(() => {
            alert.remove()
          }, 300)
        }, 3000)
      }
    })
  }

  // Utility functions
  window.MiddlewarePortal = {
    showAlert: (message, type = "info") => {
      const alertHtml = `
                <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `

      const container = document.querySelector(".container-fluid")
      if (container) {
        container.insertAdjacentHTML("afterbegin", alertHtml)
      }
    },

    confirmAction: (message, callback) => {
      if (confirm(message)) {
        callback()
      }
    },
  }
})()
