/**
 * Sidebar Navigation Script
 * Sistema de Lecturas de Medidores
 */

(function() {
    'use strict';

    // Elementos del DOM
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const body = document.body;

    // Constantes
    const STORAGE_KEY = 'sidebar-collapsed';
    const MOBILE_BREAKPOINT = 768;

    /**
     * Verifica si estamos en mobile
     */
    function isMobile() {
        return window.innerWidth <= MOBILE_BREAKPOINT;
    }

    /**
     * Inicializa el estado del sidebar desde localStorage
     */
    function initSidebarState() {
        // Solo aplicar estado colapsado en desktop
        if (!isMobile()) {
            const isCollapsed = localStorage.getItem(STORAGE_KEY) === 'true';
            if (isCollapsed) {
                sidebar.classList.add('collapsed');
                body.classList.add('sidebar-collapsed');
            }
        }
    }

    /**
     * Toggle del sidebar en desktop (colapsar/expandir)
     */
    function toggleSidebar() {
        if (isMobile()) return; // No aplicar en mobile

        const isCollapsed = sidebar.classList.toggle('collapsed');
        body.classList.toggle('sidebar-collapsed');

        // Guardar estado en localStorage
        localStorage.setItem(STORAGE_KEY, isCollapsed);

        // Animar el icono del toggle
        animateToggleIcon();
    }

    /**
     * Abre el sidebar en mobile
     */
    function openSidebarMobile() {
        sidebar.classList.add('active');
        sidebarOverlay.classList.add('active');
        body.style.overflow = 'hidden';
    }

    /**
     * Cierra el sidebar en mobile
     */
    function closeSidebarMobile() {
        sidebar.classList.remove('active');
        sidebarOverlay.classList.remove('active');
        body.style.overflow = '';
    }

    /**
     * Toggle del sidebar en mobile
     */
    function toggleSidebarMobile() {
        if (sidebar.classList.contains('active')) {
            closeSidebarMobile();
        } else {
            openSidebarMobile();
        }
    }

    /**
     * Anima el icono del toggle button
     */
    function animateToggleIcon() {
        const icon = sidebarToggle.querySelector('i');
        icon.style.transform = 'rotate(180deg)';
        setTimeout(() => {
            icon.style.transform = 'rotate(0deg)';
        }, 300);
    }

    /**
     * Cierra el sidebar mobile al hacer clic en un link
     */
    function handleMenuLinkClick(e) {
        if (isMobile() && !e.target.closest('.has-submenu')) {
            // Pequeño delay para que se vea la transición
            setTimeout(() => {
                closeSidebarMobile();
            }, 200);
        }
    }

    /**
     * Maneja el resize de la ventana
     */
    function handleResize() {
        if (isMobile()) {
            // En mobile, asegurarse de que el sidebar no esté collapsed
            sidebar.classList.remove('collapsed');
            body.classList.remove('sidebar-collapsed');
        } else {
            // En desktop, cerrar el menú mobile si estaba abierto
            closeSidebarMobile();

            // Restaurar estado collapsed si estaba guardado
            const isCollapsed = localStorage.getItem(STORAGE_KEY) === 'true';
            if (isCollapsed) {
                sidebar.classList.add('collapsed');
                body.classList.add('sidebar-collapsed');
            }
        }
    }

    /**
     * Debounce function para el resize
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Inicializa todos los event listeners
     */
    function initEventListeners() {
        // Toggle button desktop
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', toggleSidebar);
        }

        // Menu button mobile
        if (mobileMenuBtn) {
            mobileMenuBtn.addEventListener('click', toggleSidebarMobile);
        }

        // Overlay mobile
        if (sidebarOverlay) {
            sidebarOverlay.addEventListener('click', closeSidebarMobile);
        }

        // Cerrar al hacer clic en un link (mobile)
        const menuLinks = sidebar.querySelectorAll('.menu-link');
        menuLinks.forEach(link => {
            link.addEventListener('click', handleMenuLinkClick);
        });

        // Manejar resize con debounce
        window.addEventListener('resize', debounce(handleResize, 250));

        // Cerrar con tecla ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && isMobile() && sidebar.classList.contains('active')) {
                closeSidebarMobile();
            }
        });
    }

    /**
     * Mejora de accesibilidad
     */
    function initAccessibility() {
        // Agregar aria-labels
        if (sidebarToggle) {
            sidebarToggle.setAttribute('aria-label', 'Toggle sidebar');
            sidebarToggle.setAttribute('aria-expanded', !sidebar.classList.contains('collapsed'));
        }

        if (mobileMenuBtn) {
            mobileMenuBtn.setAttribute('aria-label', 'Open menu');
        }

        // Actualizar aria-expanded al hacer toggle
        if (sidebarToggle) {
            const originalToggle = sidebarToggle.onclick;
            sidebarToggle.onclick = function(e) {
                if (originalToggle) originalToggle.call(this, e);
                const isCollapsed = sidebar.classList.contains('collapsed');
                this.setAttribute('aria-expanded', !isCollapsed);
            };
        }
    }

    /**
     * Animación de entrada del sidebar (deshabilitada para evitar pestañeo)
     */
    function animateEntrance() {
        // Deshabilitada para evitar FOUC (Flash of Unstyled Content)
        // El sidebar ahora se muestra inmediatamente sin animación
    }

    /**
     * Marca el item activo en el menú basado en la URL actual
     */
    function highlightActiveMenuItem() {
        const currentPath = window.location.pathname;
        const menuLinks = sidebar.querySelectorAll('.menu-link');

        menuLinks.forEach(link => {
            const href = link.getAttribute('href');

            // Remover clase active de todos
            link.classList.remove('active');

            // Agregar clase active al que coincide
            if (href && currentPath.startsWith(href) && href !== '/') {
                link.classList.add('active');
            } else if (href === '/' && currentPath === '/') {
                link.classList.add('active');
            }
        });
    }

    /**
     * Inicialización principal
     */
    function init() {
        console.log('Initializing sidebar...');

        // Inicializar estado del sidebar
        initSidebarState();

        // Inicializar event listeners
        initEventListeners();

        // Inicializar accesibilidad
        initAccessibility();

        // Animar entrada
        animateEntrance();

        // Highlight active menu item
        highlightActiveMenuItem();

        console.log('Sidebar initialized successfully');
    }

    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Exponer funciones globales si es necesario
    window.Sidebar = {
        toggle: toggleSidebar,
        open: openSidebarMobile,
        close: closeSidebarMobile,
        isMobile: isMobile
    };

})();
