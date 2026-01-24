/**
 * components.js - Reusable UI Components
 * Sistema de Lecturas de Medidores
 *
 * Provides: Toast, ConfirmModal, Loading, FilterBar
 */
(function() {
    'use strict';

    // ==============================
    // TOAST NOTIFICATIONS
    // ==============================

    var Toast = {
        container: null,

        _ensureContainer: function() {
            if (!this.container) {
                this.container = document.createElement('div');
                this.container.className = 'toast-container';
                this.container.setAttribute('aria-live', 'polite');
                document.body.appendChild(this.container);
            }
        },

        /**
         * Show a toast notification
         * @param {string} message - The message to display
         * @param {string} type - 'success' | 'error' | 'warning' | 'info'
         * @param {number} duration - Auto-dismiss in ms (default 4000, 0 = manual)
         */
        show: function(message, type, duration) {
            type = type || 'info';
            duration = duration !== undefined ? duration : 4000;

            this._ensureContainer();

            var icons = {
                success: 'fa-check-circle',
                error: 'fa-times-circle',
                warning: 'fa-exclamation-triangle',
                info: 'fa-info-circle'
            };

            var toast = document.createElement('div');
            toast.className = 'toast toast--' + type;
            toast.setAttribute('role', 'alert');
            toast.innerHTML =
                '<span class="toast__icon"><i class="fas ' + (icons[type] || icons.info) + '"></i></span>' +
                '<span class="toast__message">' + message + '</span>' +
                '<button class="toast__close" aria-label="Cerrar">&times;</button>';

            var self = this;
            var closeBtn = toast.querySelector('.toast__close');
            closeBtn.addEventListener('click', function() {
                self._dismiss(toast);
            });

            this.container.appendChild(toast);

            if (duration > 0) {
                setTimeout(function() {
                    self._dismiss(toast);
                }, duration);
            }

            return toast;
        },

        _dismiss: function(toast) {
            if (!toast || !toast.parentNode) return;
            toast.classList.add('toast--exiting');
            setTimeout(function() {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
            }, 200);
        },

        success: function(msg, dur) { return this.show(msg, 'success', dur); },
        error: function(msg, dur) { return this.show(msg, 'error', dur); },
        warning: function(msg, dur) { return this.show(msg, 'warning', dur); },
        info: function(msg, dur) { return this.show(msg, 'info', dur); }
    };

    // ==============================
    // CONFIRM/PROMPT MODAL
    // ==============================

    var ConfirmModal = {
        _modal: null,

        /**
         * Show a confirmation dialog
         * @param {Object} options
         * @param {string} options.title - Modal title
         * @param {string} options.message - Modal body text
         * @param {string} options.icon - 'warning' | 'danger' | 'success' | 'info'
         * @param {string} options.confirmText - Confirm button text (default 'Confirmar')
         * @param {string} options.cancelText - Cancel button text (default 'Cancelar')
         * @param {string} options.confirmClass - Confirm button class (default 'btn--primary')
         * @param {boolean} options.showInput - Show a text input field
         * @param {string} options.inputLabel - Label for the input field
         * @param {string} options.inputPlaceholder - Placeholder for input
         * @param {boolean} options.inputRequired - Whether input is required (default true)
         * @returns {Promise<string|boolean>} - Resolves with input value or true; false on cancel
         */
        show: function(options) {
            var self = this;
            options = options || {};

            var title = options.title || 'Confirmar';
            var message = options.message || '';
            var icon = options.icon || 'warning';
            var confirmText = options.confirmText || 'Confirmar';
            var cancelText = options.cancelText || 'Cancelar';
            var confirmClass = options.confirmClass || 'btn--primary';
            var showInput = options.showInput || false;
            var inputLabel = options.inputLabel || '';
            var inputPlaceholder = options.inputPlaceholder || '';
            var inputRequired = options.inputRequired !== false;

            var iconClasses = {
                warning: 'fa-exclamation-triangle',
                danger: 'fa-times-circle',
                success: 'fa-check-circle',
                info: 'fa-info-circle'
            };

            var inputHtml = '';
            if (showInput) {
                inputHtml = '<div class="form-group" style="margin-top: var(--spacing-md);">' +
                    (inputLabel ? '<label>' + inputLabel + '</label>' : '') +
                    '<textarea id="confirm-modal-input" rows="3" placeholder="' + inputPlaceholder + '"' +
                    ' style="width:100%;min-height:80px;padding:8px;border:1px solid var(--color-border);border-radius:4px;font-size:14px;resize:vertical;"' +
                    (inputRequired ? ' required' : '') + '></textarea></div>';
            }

            var html =
                '<div class="modal__content">' +
                '<div class="modal__drag-indicator"></div>' +
                '<div class="modal__header"><h3>' + title + '</h3>' +
                '<button class="modal__close" data-action="cancel">&times;</button></div>' +
                '<div class="modal__body">' +
                '<div class="modal__icon modal__icon--' + icon + '">' +
                '<i class="fas ' + (iconClasses[icon] || iconClasses.warning) + '"></i></div>' +
                '<p class="modal__text">' + message + '</p>' +
                inputHtml +
                '<div class="modal__actions">' +
                '<button class="btn btn--secondary" data-action="cancel">' + cancelText + '</button>' +
                '<button class="btn ' + confirmClass + '" data-action="confirm">' + confirmText + '</button>' +
                '</div></div></div>';

            // Remove existing
            if (self._modal && self._modal.parentNode) {
                self._modal.parentNode.removeChild(self._modal);
            }

            self._modal = document.createElement('div');
            self._modal.className = 'modal active';
            self._modal.id = 'confirmModal';
            self._modal.innerHTML = html;
            document.body.appendChild(self._modal);

            // Focus input if present
            if (showInput) {
                setTimeout(function() {
                    var input = document.getElementById('confirm-modal-input');
                    if (input) input.focus();
                }, 100);
            }

            return new Promise(function(resolve) {
                function handleClick(e) {
                    var target = e.target.closest('[data-action]');
                    var action = target ? target.dataset.action : null;

                    // Click on overlay
                    if (e.target === self._modal) action = 'cancel';

                    if (!action) return;

                    if (action === 'confirm') {
                        if (showInput) {
                            var inputVal = document.getElementById('confirm-modal-input').value.trim();
                            if (inputRequired && !inputVal) {
                                Toast.warning('Este campo es obligatorio');
                                return;
                            }
                            cleanup();
                            resolve(inputVal);
                        } else {
                            cleanup();
                            resolve(true);
                        }
                    } else if (action === 'cancel') {
                        cleanup();
                        resolve(false);
                    }
                }

                function handleKey(e) {
                    if (e.key === 'Escape') {
                        cleanup();
                        resolve(false);
                    }
                }

                function cleanup() {
                    self._modal.removeEventListener('click', handleClick);
                    document.removeEventListener('keydown', handleKey);
                    if (self._modal && self._modal.parentNode) {
                        self._modal.parentNode.removeChild(self._modal);
                    }
                    self._modal = null;
                }

                self._modal.addEventListener('click', handleClick);
                document.addEventListener('keydown', handleKey);
            });
        }
    };

    // ==============================
    // LOADING STATE
    // ==============================

    var Loading = {
        /**
         * Show loading overlay on an element
         * @param {HTMLElement} element - Target element
         * @returns {HTMLElement} - The overlay element (for removal)
         */
        show: function(element) {
            if (!element) return null;
            var pos = window.getComputedStyle(element).position;
            if (pos === 'static') element.style.position = 'relative';
            var overlay = document.createElement('div');
            overlay.className = 'loading-overlay';
            overlay.innerHTML = '<div class="loading-spinner"></div>';
            element.appendChild(overlay);
            return overlay;
        },

        /**
         * Remove loading overlay
         * @param {HTMLElement} overlay
         */
        hide: function(overlay) {
            if (overlay && overlay.parentNode) {
                overlay.parentNode.removeChild(overlay);
            }
        }
    };

    // ==============================
    // FILTER BAR AUTO-SUBMIT
    // ==============================

    var FilterBar = {
        /**
         * Initialize auto-submit on filter change
         * @param {string} formSelector - CSS selector for the filter form
         * @param {Object} options
         * @param {number} options.debounceMs - Debounce delay (default 300)
         * @param {string} options.containerSelector - Content container to show loading on
         */
        init: function(formSelector, options) {
            options = options || {};
            var form = document.querySelector(formSelector);
            if (!form) return;

            var debounceMs = options.debounceMs || 300;
            var containerSelector = options.containerSelector || null;
            var timer = null;

            function submitWithLoading() {
                if (containerSelector) {
                    var container = document.querySelector(containerSelector);
                    if (container) Loading.show(container);
                }
                form.submit();
            }

            var selects = form.querySelectorAll('select');
            var checkboxes = form.querySelectorAll('input[type="checkbox"]');

            selects.forEach(function(select) {
                select.addEventListener('change', function() {
                    clearTimeout(timer);
                    timer = setTimeout(submitWithLoading, debounceMs);
                });
            });

            checkboxes.forEach(function(cb) {
                cb.addEventListener('change', function() {
                    clearTimeout(timer);
                    timer = setTimeout(submitWithLoading, debounceMs);
                });
            });
        }
    };

    // Expose globally
    window.Toast = Toast;
    window.ConfirmModal = ConfirmModal;
    window.Loading = Loading;
    window.FilterBar = FilterBar;

})();
