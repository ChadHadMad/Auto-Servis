/**
 * nav.js — Shared navigation bar za sve Autoservis stranice.
 * Ubaci <script src="/nav.js"></script> prije </body> na svakoj stranici.
 * Automatski detektira aktivnu stranicu i role korisnika.
 */

(function () {
  const PAGES = [
    { href: "/index.html",        label: "Prijava",          icon: "⚙",  roles: ["*"],                    hideIfLoggedIn: true  },
    { href: "/dashboard.html",    label: "Dashboard",        icon: "⊞",  roles: ["customer","mechanic","admin"] },
    { href: "/customer.html",     label: "Narudžbe",         icon: "📋", roles: ["customer"]               },
    { href: "/mechanic.html",     label: "Narudžbe",         icon: "🔩", roles: ["mechanic"]               },
    { href: "/admin.html",        label: "Admin",            icon: "👤", roles: ["admin"]                  },
    { href: "/service-book.html", label: "Servisna knjižica",icon: "📖", roles: ["mechanic","admin"]       },
    { href: "/ml-dashboard.html", label: "ML Predikcija",    icon: "🔮", roles: ["mechanic","admin"]       },
    { href: "/chat.html",         label: "AI Pomoć",         icon: "💬", roles: ["*"]                      },
    { href: "/chat-admin.html",   label: "RAG Admin",        icon: "🗂", roles: ["admin"]                  },
  ];

  function currentRole() {
    return localStorage.getItem("role") || null;
  }

  function isLoggedIn() {
    return !!localStorage.getItem("token");
  }

  function currentPath() {
    return window.location.pathname.replace(/\/$/, "") || "/index.html";
  }

  function visiblePages() {
    const role = currentRole();
    const loggedIn = isLoggedIn();
    return PAGES.filter(p => {
      if (p.hideIfLoggedIn && loggedIn) return false;
      if (p.roles.includes("*")) return true;
      if (!role) return false;
      return p.roles.includes(role);
    });
  }

  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    window.location.href = "/index.html";
  }

  function inject() {
    const path = currentPath();
    const role = currentRole();
    const loggedIn = isLoggedIn();
    const pages = visiblePages();

    const navLinks = pages.map(p => {
      const isActive = path.endsWith(p.href.replace("/", "")) || path === p.href;
      return `
        <a href="${p.href}" class="as-nav-link${isActive ? " as-nav-active" : ""}">
          <span class="as-nav-icon">${p.icon}</span>
          <span class="as-nav-label">${p.label}</span>
        </a>`;
    }).join("");

    const ROLE_LABELS = { admin: "Admin", mechanic: "Mehaničar", customer: "Korisnik" };
    const roleLabel = ROLE_LABELS[role] || role || "?";
    const userChip = loggedIn
      ? `<span class="as-nav-role">${roleLabel}</span>
         <button class="as-nav-logout" onclick="__asLogout()">Odjava</button>`
      : "";

    const html = `
      <nav class="as-navbar" id="as-navbar">
        <a href="/index.html" class="as-nav-brand">
          <span class="as-nav-brand-icon">🔧</span>
          <span class="as-nav-brand-name">AutoServis</span>
        </a>
        <div class="as-nav-links" id="as-nav-links">
          ${navLinks}
        </div>
        <div class="as-nav-end">
          ${userChip}
          <button class="as-nav-hamburger" id="as-hamburger" onclick="__asToggleMenu()" aria-label="Menu">
            <span></span><span></span><span></span>
          </button>
        </div>
      </nav>
      <div class="as-nav-spacer"></div>
    `;

    const css = `
      <style id="as-nav-style">
        :root {
          --as-nav-h: 54px;
          --as-bg: #ffffff;
          --as-border: #e8e6e1;
          --as-text: #1a1916;
          --as-text2: #6b6860;
          --as-text3: #9c9990;
          --as-accent: #1a1916;
          --as-accent-hover: #333;
          --as-active-bg: #f0eeea;
          --as-active-border: #1a1916;
          --as-font: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }

        * { box-sizing: border-box; }

        .as-navbar {
          position: fixed;
          top: 0; left: 0; right: 0;
          height: var(--as-nav-h);
          background: var(--as-bg);
          border-bottom: 1px solid var(--as-border);
          display: flex;
          align-items: center;
          gap: 0;
          padding: 0 20px;
          z-index: 1000;
          font-family: var(--as-font);
        }

        .as-nav-brand {
          display: flex;
          align-items: center;
          gap: 8px;
          text-decoration: none;
          color: var(--as-text);
          font-weight: 700;
          font-size: 15px;
          letter-spacing: -0.3px;
          white-space: nowrap;
          margin-right: 8px;
          padding-right: 16px;
          border-right: 1px solid var(--as-border);
          flex-shrink: 0;
        }

        .as-nav-brand-icon { font-size: 18px; }

        .as-nav-links {
          display: flex;
          align-items: center;
          gap: 2px;
          flex: 1;
          overflow-x: auto;
          scrollbar-width: none;
          padding: 0 8px;
        }
        .as-nav-links::-webkit-scrollbar { display: none; }

        .as-nav-link {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 10px;
          border-radius: 8px;
          text-decoration: none;
          color: var(--as-text2);
          font-size: 13px;
          font-weight: 500;
          white-space: nowrap;
          transition: background 0.12s, color 0.12s;
          font-family: var(--as-font);
          border: 1px solid transparent;
        }

        .as-nav-link:hover {
          background: var(--as-active-bg);
          color: var(--as-text);
        }

        .as-nav-active {
          background: var(--as-active-bg);
          color: var(--as-text);
          border-color: var(--as-border);
          font-weight: 600;
        }

        .as-nav-icon { font-size: 14px; line-height: 1; }
        .as-nav-label { line-height: 1; }

        .as-nav-end {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-shrink: 0;
          margin-left: 8px;
          padding-left: 12px;
          border-left: 1px solid var(--as-border);
        }

        .as-nav-role {
          font-size: 11px;
          font-weight: 600;
          color: var(--as-text3);
          background: var(--as-active-bg);
          border: 1px solid var(--as-border);
          border-radius: 20px;
          padding: 3px 10px;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          white-space: nowrap;
        }

        .as-nav-logout {
          font-size: 12px;
          font-weight: 500;
          color: #c0392b;
          background: #fdf0ef;
          border: 1px solid #f5c6c2;
          border-radius: 8px;
          padding: 5px 12px;
          cursor: pointer;
          font-family: var(--as-font);
          transition: opacity 0.12s;
          white-space: nowrap;
        }
        .as-nav-logout:hover { opacity: 0.8; }

        .as-nav-hamburger {
          display: none;
          flex-direction: column;
          justify-content: center;
          gap: 4px;
          width: 32px;
          height: 32px;
          background: none;
          border: 1px solid var(--as-border);
          border-radius: 8px;
          cursor: pointer;
          padding: 6px 7px;
        }
        .as-nav-hamburger span {
          display: block;
          height: 1.5px;
          background: var(--as-text2);
          border-radius: 2px;
          transition: all 0.2s;
        }

        .as-nav-spacer { height: var(--as-nav-h); flex-shrink: 0; display: block; }

        @media (max-width: 700px) {
          .as-nav-brand-name { display: none; }
          .as-nav-label { display: none; }
          .as-nav-links { gap: 0; padding: 0 4px; }
          .as-nav-link { padding: 6px 8px; }
          .as-nav-role { display: none; }
          .as-nav-hamburger { display: flex; }

          .as-nav-links {
            position: fixed;
            top: var(--as-nav-h);
            left: 0; right: 0;
            background: var(--as-bg);
            border-bottom: 1px solid var(--as-border);
            flex-direction: column;
            align-items: stretch;
            padding: 8px 16px 16px;
            gap: 4px;
            overflow-x: visible;
            transform: translateY(-110%);
            transition: transform 0.2s ease;
            z-index: 999;
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
          }

          .as-nav-links.as-open {
            transform: translateY(0);
          }

          .as-nav-links.as-open .as-nav-label { display: inline; }

          .as-nav-link {
            padding: 10px 12px;
            border-radius: 8px;
            font-size: 14px;
          }

          .as-nav-logout { font-size: 11px; padding: 4px 10px; }
        }
      </style>
    `;

    // Inject CSS in head
    if (!document.getElementById("as-nav-style")) {
      document.head.insertAdjacentHTML("beforeend", css);
    }

    // Inject navbar before body content
    const wrapper = document.createElement("div");
    wrapper.innerHTML = html;
    document.body.insertBefore(wrapper, document.body.firstChild);

    // Push body content down (in case page has fixed elements)
    // Already handled by .as-nav-spacer
  }

  // Global functions
  window.__asLogout = logout;
  window.__asToggleMenu = function () {
    const links = document.getElementById("as-nav-links");
    if (links) links.classList.toggle("as-open");
  };

  // Run after DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", inject);
  } else {
    inject();
  }
})();