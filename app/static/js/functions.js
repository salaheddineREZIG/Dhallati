class EnhancedNotificationManager {
        constructor() {
            this.badge = document.getElementById('notificationCount');
            this.dropdown = document.getElementById('notificationList');
            this.unreadCount = 0;
            this.initialize();
        }
        
        async initialize() {
            await this.loadNotifications();
            this.setupEventListeners();
            this.startPolling();
        }
        
        setupEventListeners() {
            // Mark all as read
            document.getElementById('markAllReadBtn')?.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.markAllAsRead();
            });
            
            // Refresh notifications
            document.getElementById('refreshNotifications')?.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.loadNotifications(true);
            });
        }
        
        async loadNotifications(showLoading = false) {
            try {
                if (showLoading) {
                    this.showLoading();
                }
                
                const response = await fetch('/lost_and_found/api/notifications');
                if (!response.ok) throw new Error('Failed to load notifications');
                
                const data = await response.json();
                this.unreadCount = data.unread_count || 0;
                this.updateBadge();
                this.renderNotifications(data.notifications || []);
            } catch (error) {
                console.error('Error loading notifications:', error);
                this.showError();
            }
        }
        
        updateBadge() {
            if (!this.badge) return;
            
            if (this.unreadCount > 0) {
                this.badge.textContent = this.unreadCount > 99 ? '99+' : this.unreadCount;
                this.badge.style.display = 'flex';
                this.badge.classList.add('badge-pulse');
            } else {
                this.badge.style.display = 'none';
                this.badge.classList.remove('badge-pulse');
            }
        }
        
        renderNotifications(notifications) {
            if (!this.dropdown) return;
            
            if (!notifications || notifications.length === 0) {
                this.dropdown.innerHTML = `
                    <div class="text-center py-4 text-muted">
                        <i class="bi bi-bell-slash fs-3 mb-2 d-block"></i>
                        <p class="mb-0">No notifications yet</p>
                        <small class="text-muted">We'll notify you when something happens</small>
                    </div>
                `;
                return;
            }
            
            const items = notifications.map(notif => this.createNotificationItem(notif)).join('');
            this.dropdown.innerHTML = items;
            
            // Add click handlers
            this.dropdown.querySelectorAll('.notification-item').forEach(item => {
                item.addEventListener('click', async (e) => {
                    e.preventDefault();
                    const notificationId = item.dataset.id;
                    const link = item.dataset.link;
                    
                    await this.markAsRead(notificationId);
                    
                    if (link && link !== '#') {
                        window.location.href = link;
                    }
                    
                    // Close dropdown
                    const dropdown = bootstrap.Dropdown.getInstance(document.getElementById('notificationDropdown'));
                    if (dropdown) dropdown.hide();
                });
            });
        }
        
        createNotificationItem(notification) {
            const timeAgo = this.getTimeAgo(notification.created_at);
            const isUnread = !notification.is_read;
            const icon = this.getNotificationIcon(notification.notification_type);
            const isDark = document.body.classList.contains('dark-theme');
            const iconColor = isDark ? 'text-warning' : this.getNotificationIconColor(notification.notification_type);
            
            return `
                <li class="dropdown-item notification-item-enhanced p-3 ${isUnread ? 'unread' : ''}" 
                    data-id="${notification.id}" 
                    data-link="${notification.link || '#'}"
                    style="cursor: pointer;">
                    <div class="d-flex align-items-start">
                        <div class="notification-icon-wrapper">
                            <i class="bi ${icon} ${iconColor}" data-type="${notification.notification_type}"></i>
                        </div>
                        <div class="flex-grow-1">
                            <p class="mb-1 ${isUnread ? 'fw-bold' : ''}">${notification.message}</p>
                            <div class="notification-time">
                                <i class="bi bi-clock"></i>
                                <span>${timeAgo}</span>
                            </div>
                        </div>
                        ${isUnread ? '<span class="badge bg-primary rounded-pill ms-2">New</span>' : ''}
                    </div>
                </li>
            `;
        }
        
        getNotificationIcon(type) {
            const icons = {
                'item_found': 'bi-search',
                'claim_request': 'bi-person-badge',
                'claim_request_anonymous': 'bi-person-badge-fill',
                'claim_accepted': 'bi-check-circle',
                'claim_rejected': 'bi-x-circle',
                'claim_cancelled': 'bi-slash-circle',
                'claim_accepted_confirmation': 'bi-check-circle-fill',
                'item_returned': 'bi-arrow-return-right',
                'item_claimed': 'bi-hand-thumbs-up',
                'item_recovered': 'bi-check-square'
            };
            return icons[type] || 'bi-bell';
        }
        
        getNotificationIconColor(type) {
            const colors = {
                'item_found': 'text-success',
                'claim_request': 'text-primary',
                'claim_request_anonymous': 'text-primary',
                'claim_accepted': 'text-success',
                'claim_rejected': 'text-danger',
                'claim_cancelled': 'text-warning',
                'claim_accepted_confirmation': 'text-success',
                'item_returned': 'text-info',
                'item_claimed': 'text-success',
                'item_recovered': 'text-success'
            };
            return colors[type] || 'text-secondary';
        }
        
        getTimeAgo(dateString) {
            if (!dateString) return 'Just now';
            const date = new Date(dateString);
            const now = new Date();
            const seconds = Math.floor((now - date) / 1000);
            
            if (seconds < 60) return "Just now";
            if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
            if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
            if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
            return date.toLocaleDateString();
        }
        
        showLoading() {
            if (!this.dropdown) return;
            this.dropdown.innerHTML = `
                <div class="text-center py-4">
                    <div class="spinner-border text-primary mb-3" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="text-muted mb-0">Loading notifications...</p>
                </div>
            `;
        }
        
        showError() {
            if (!this.dropdown) return;
            this.dropdown.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="bi bi-exclamation-triangle fs-3 mb-2 d-block"></i>
                    <p class="mb-2">Failed to load notifications</p>
                    <button class="btn btn-sm btn-primary" onclick="window.notificationManager.loadNotifications(true)">
                        Retry
                    </button>
                </div>
            `;
        }
        
        async markAsRead(notificationId) {
            try {
                const response = await fetch(`/lost_and_found/api/notifications/${notificationId}/read`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.ok) {
                    this.unreadCount = Math.max(0, this.unreadCount - 1);
                    this.updateBadge();
                    
                    // Update UI
                    const notificationItem = document.querySelector(`.notification-item-enhanced[data-id="${notificationId}"]`);
                    if (notificationItem) {
                        notificationItem.classList.remove('unread', 'fw-bold');
                        notificationItem.querySelector('.badge')?.remove();
                    }
                }
            } catch (error) {
                console.error('Error marking notification as read:', error);
            }
        }
        
        async markAllAsRead() {
            try {
                const response = await fetch('/lost_and_found/api/notifications/read_all', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.ok) {
                    this.unreadCount = 0;
                    this.updateBadge();
                    
                    // Update all notifications
                    document.querySelectorAll('.notification-item-enhanced').forEach(item => {
                        item.classList.remove('unread', 'fw-bold');
                        item.querySelector('.badge')?.remove();
                    });
                }
            } catch (error) {
                console.error('Error marking all notifications as read:', error);
                this.showToast('Failed to mark all notifications as read', 'danger');
            }
        }
        
        startPolling() {
            setInterval(() => this.loadNotifications(), 30000); // Poll every 30 seconds
        }
        
        showToast(message, type = 'info') {
            // Create toast notification
            const toast = document.createElement('div');
            toast.className = `toast align-items-center text-bg-${type} border-0 show`;
            toast.setAttribute('role', 'alert');
            toast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            `;
            
            const container = document.getElementById('flash-container') || document.body;
            container.appendChild(toast);
            
            setTimeout(() => toast.remove(), 3000);
        }
    }
    
    // Initialize notification manager
    if (document.getElementById('notificationDropdown')) {
        window.notificationManager = new EnhancedNotificationManager();
    }