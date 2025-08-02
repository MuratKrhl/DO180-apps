/**
 * Theme Manager - Layout ve Sidebar Yönetimi
 */

class ThemeManager {
  constructor() {
    this.settings = {
      layout: "vertical",
      sidebarSize: "lg",
      themeMode: "light",
    }

    this.init()
  }

  init() {
    this.loadSettings()
    this.applySettings()
    this.bindEvents()
    this.initCustomizer()
  }

  // LocalStorage'dan ayarları yükle
  loadSettings() {
    const savedSettings = localStorage.getItem("middleware-portal-theme")
    if (savedSettings) {
      this.settings = { ...this.settings, ...JSON.parse(savedSettings) }
    }
  }

  // Ayarları localStorage'a kaydet
  saveSettings() {
    localStorage.setItem("middleware-portal-theme", JSON.stringify(this.settings))
  }

  // Ayarları DOM'a uygula
  applySettings() {
    const html = document.documentElement
    const body = document.body

    // Layout ayarı
    body.setAttribute("data-layout", this.settings.layout)

    // Sidebar boyutu
    body.setAttribute("data-sidebar-size", this.settings.sidebarSize)

    // Tema modu
    html.setAttribute("data-bs-theme", this.settings.themeMode)

    // Layout'a göre özel sınıflar
    this.applyLayoutClasses()

    // Sidebar davranışını ayarla
    this.applySidebarBehavior()
  }

  applyLayoutClasses() {
    const body = document.body
    const layoutClasses = ["vertical-layout", "horizontal-layout", "twocolumn-layout", "semibox-layout"]

    // Mevcut layout sınıflarını temizle
    body.classList.remove(...layoutClasses)

    // Yeni layout sınıfını ekle
    body.classList.add(`${this.settings.layout}-layout`)

    // Layout'a göre özel düzenlemeler
    switch (this.settings.layout) {
      case "horizontal":
        this.setupHorizontalLayout()
        break
      case "twocolumn":
        this.setupTwoColumnLayout()
        break
      case "semibox":
        this.setupSemiBoxLayout()
        break
      default:
        this.setupVerticalLayout()
    }
  }

  applySidebarBehavior() {
    const sidebar = document.querySelector(".app-menu")
    if (!sidebar) return

    // Mevcut sidebar sınıflarını temizle
    const sizeClasses = ["sidebar-lg", "sidebar-md", "sidebar-sm", "sidebar-sm-hover"]
    sidebar.classList.remove(...sizeClasses)

    // Yeni sidebar sınıfını ekle
    sidebar.classList.add(`sidebar-${this.settings.sidebarSize}`)

    // Hover davranışı için özel işlem
    if (this.settings.sidebarSize === "sm-hover") {
      this.setupHoverSidebar()
    }
  }

  setupVerticalLayout() {
    const sidebar = document.querySelector(".app-menu")
    const mainContent = document.querySelector(".main-content")

    if (sidebar) sidebar.style.display = "block"
    if (mainContent) {
      mainContent.style.marginLeft = "250px"
      mainContent.style.marginTop = "70px"
    }
  }

  setupHorizontalLayout() {
    const sidebar = document.querySelector(".app-menu")
    const mainContent = document.querySelector(".main-content")
    const topbar = document.querySelector("#page-topbar")

    if (sidebar) sidebar.style.display = "none"
    if (mainContent) {
      mainContent.style.marginLeft = "0"
      mainContent.style.marginTop = "120px" // Topbar + horizontal menu
    }

    // Horizontal menüyü oluştur/göster
    this.createHorizontalMenu()
  }

  setupTwoColumnLayout() {
    const sidebar = document.querySelector(".app-menu")
    const mainContent = document.querySelector(".main-content")

    if (sidebar) {
      sidebar.style.display = "block"
      sidebar.classList.add("two-column-menu")
    }

    if (mainContent) {
      mainContent.style.marginLeft = "300px" // Daha geniş sidebar
      mainContent.style.marginTop = "70px"
    }
  }

  setupSemiBoxLayout() {
    const mainContent = document.querySelector(".main-content")

    if (mainContent) {
      mainContent.style.marginLeft = "250px"
      mainContent.style.marginTop = "70px"
      mainContent.style.padding = "24px"
      mainContent.style.background = "#f3f3f9"
    }

    // İçerik alanına box stili ekle
    const pageContent = document.querySelector(".page-content")
    if (pageContent) {
      pageContent.style.background = "#fff"
      pageContent.style.borderRadius = "8px"
      pageContent.style.boxShadow = "0 2px 4px rgba(15, 34, 58, 0.12)"
    }
  }

  setupHoverSidebar() {
    const sidebar = document.querySelector(".app-menu")
    if (!sidebar) return

    let hoverTimeout

    sidebar.addEventListener("mouseenter", () => {
      clearTimeout(hoverTimeout)
      sidebar.classList.add("sidebar-expanded")
    })

    sidebar.addEventListener("mouseleave", () => {
      hoverTimeout = setTimeout(() => {
        sidebar.classList.remove("sidebar-expanded")
      }, 300)
    })
  }

  createHorizontalMenu() {
    let horizontalMenu = document.querySelector(".horizontal-menu")

    if (!horizontalMenu) {
      horizontalMenu = document.createElement("div")
      horizontalMenu.className = "horizontal-menu"
      horizontalMenu.innerHTML = this.getHorizontalMenuHTML()

      const topbar = document.querySelector("#page-topbar")
      if (topbar) {
        topbar.insertAdjacentElement("afterend", horizontalMenu)
      }
    }

    horizontalMenu.style.display = "block"
  }

  getHorizontalMenuHTML() {
    return `
            <div class="container-fluid">
                <nav class="navbar navbar-expand-lg horizontal-navbar">
                    <div class="navbar-nav">
                        <a class="nav-link" href="/"><i class="ri-dashboard-2-line"></i> Dashboard</a>
                        <div class="nav-item dropdown">
                            <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
                                <i class="ri-server-line"></i> Envanter
                            </a>
                            <div class="dropdown-menu">
                                <a class="dropdown-item" href="/inventory/servers/">Sunucular</a>
                                <a class="dropdown-item" href="/inventory/applications/">Uygulamalar</a>
                            </div>
                        </div>
                        <a class="nav-link" href="/askgt/"><i class="ri-question-answer-line"></i> AskGT</a>
                        <a class="nav-link" href="/announcements/"><i class="ri-notification-3-line"></i> Duyurular</a>
                        <a class="nav-link" href="/automation/"><i class="ri-settings-3-line"></i> Otomasyon</a>
                        <a class="nav-link" href="/performance/"><i class="ri-line-chart-line"></i> Performans</a>
                    </div>
                </nav>
            </div>
        `
  }

  // Event listener'ları bağla
  bindEvents() {
    // Layout seçimi
    document.addEventListener("change", (e) => {
      if (e.target.name === "layout") {
        this.settings.layout = e.target.value
        this.saveSettings()
        this.applySettings()
      }

      if (e.target.name === "sidebar-size") {
        this.settings.sidebarSize = e.target.value
        this.saveSettings()
        this.applySettings()
      }

      if (e.target.name === "theme-mode") {
        this.settings.themeMode = e.target.value
        this.saveSettings()
        this.applySettings()
      }
    })

    // Reset butonu
    document.addEventListener("click", (e) => {
      if (e.target.id === "reset-layout") {
        this.resetToDefaults()
      }
    })
  }

  // Customizer panelini başlat
  initCustomizer() {
    const customizerBtn = document.querySelector(".customizer-btn")
    const customizerPanel = document.querySelector(".customizer-setting-panel")
    const customizerClose = document.querySelector(".customizer-close")
    const customizerOverlay = document.querySelector(".customizer-panel-overlay")

    if (customizerBtn) {
      customizerBtn.addEventListener("click", () => {
        customizerPanel.classList.add("show")
        document.body.style.overflow = "hidden"
      })
    }

    const closeCustomizer = () => {
      customizerPanel.classList.remove("show")
      document.body.style.overflow = ""
    }

    if (customizerClose) {
      customizerClose.addEventListener("click", closeCustomizer)
    }

    if (customizerOverlay) {
      customizerOverlay.addEventListener("click", closeCustomizer)
    }

    // ESC tuşu ile kapatma
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && customizerPanel.classList.contains("show")) {
        closeCustomizer()
      }
    })

    // Mevcut ayarları form'da işaretle
    this.updateCustomizerForm()
  }

  updateCustomizerForm() {
    // Layout seçimini işaretle
    const layoutRadio = document.querySelector(`input[name="layout"][value="${this.settings.layout}"]`)
    if (layoutRadio) layoutRadio.checked = true

    // Sidebar boyutunu işaretle
    const sidebarRadio = document.querySelector(`input[name="sidebar-size"][value="${this.settings.sidebarSize}"]`)
    if (sidebarRadio) sidebarRadio.checked = true

    // Tema modunu işaretle
    const themeRadio = document.querySelector(`input[name="theme-mode"][value="${this.settings.themeMode}"]`)
    if (themeRadio) themeRadio.checked = true
  }

  resetToDefaults() {
    this.settings = {
      layout: "vertical",
      sidebarSize: "lg",
      themeMode: "light",
    }

    this.saveSettings()
    this.applySettings()
    this.updateCustomizerForm()

    // Başarı mesajı göster
    if (window.MiddlewarePortal) {
      window.MiddlewarePortal.showAlert("Ayarlar varsayılan değerlere sıfırlandı.", "success")
    }
  }
}

// Theme Manager'ı başlat
document.addEventListener("DOMContentLoaded", () => {
  window.themeManager = new ThemeManager()
})
