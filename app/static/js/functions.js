class NotificationManager {
    constructor() {
        this.badge = document.getElementById('notificationBadge');
        this.dropdown = document.getElementById('notificationList');
        this.unreadCount = 0;
        
        this.init();
        this.startPolling();
    }
    
    async init() {
        await this.loadNotifications();
        
        // Mark all as read button
        document.getElementById('markAllReadBtn')?.addEventListener('click', () => {
            this.markAllAsRead();
        });
    }
    
    async loadNotifications() {
        try {
            const response = await fetch('/lost_and_found/api/notifications');
            const data = await response.json();
            
            this.unreadCount = data.unread_count;
            this.updateBadge();
            this.renderNotifications(data.notifications);
        } catch (error) {
            console.error('Failed to load notifications:', error);
        }
    }
    
    updateBadge() {
        if (this.unreadCount > 0) {
            this.badge.textContent = this.unreadCount;
            this.badge.style.display = 'block';
        } else {
            this.badge.style.display = 'none';
        }
    }
    
    renderNotifications(notifications) {
        if (notifications.length === 0) {
            this.dropdown.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="bi bi-bell-slash fs-3"></i>
                    <p class="mb-0 mt-2">No notifications</p>
                </div>
            `;
            return;
        }
        
        const items = notifications.map(notif => this.createNotificationItem(notif)).join('');
        this.dropdown.innerHTML = items;
        
        // Add click handlers
        document.querySelectorAll('.notification-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const notificationId = item.dataset.id;
                this.markAsRead(notificationId);
                
                // Navigate to relevant page
                const link = item.dataset.link;
                if (link) {
                    window.location.href = link;
                }
            });
        });
    }
    
    createNotificationItem(notification) {
        const timeAgo = this.getTimeAgo(notification.created_at);
        const isReadClass = notification.is_read ? '' : 'fw-bold';
        
        // Determine link based on notification type
        let link = '';
        if (notification.notification_type === 'claim_request') {
            link = `/lost_and_found/claims/manage?claim_id=${notification.related_id}`;
        } else if (notification.item_id) {
            link = `/lost_and_found/items/${notification.item_id}`;
        }
        
        return `
            <div class="notification-item dropdown-item p-3 border-bottom" 
                 data-id="${notification.id}" 
                 data-link="${link}"
                 style="cursor: pointer;">
                <div class="d-flex">
                    <div class="flex-shrink-0">
                        <i class="bi ${this.getNotificationIcon(notification.notification_type)}"></i>
                    </div>
                    <div class="flex-grow-1 ms-3">
                        <p class="mb-1 ${isReadClass}">${notification.message}</p>
                        <small class="text-muted">${timeAgo}</small>
                    </div>
                </div>
            </div>
        `;
    }
    
    getNotificationIcon(type) {
        const icons = {
            'claim_request': 'bi-person-badge',
            'claim_accepted': 'bi-check-circle',
            'claim_rejected': 'bi-x-circle',
            'item_found': 'bi-search',
            'match_found': 'bi-shuffle'
        };
        return icons[type] || 'bi-bell';
    }
    
    getTimeAgo(dateString) {
        // Implement time ago function
        return moment(dateString).fromNow();
    }getTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    let interval = Math.floor(seconds / 31536000);
    if (interval >= 1) {
        return interval + " year" + (interval > 1 ? "s" : "") + " ago";
    }
    interval = Math.floor(seconds / 2592000);
    if (interval >= 1) {
        return interval + " month" + (interval > 1 ? "s" : "") + " ago";
    }
    interval = Math.floor(seconds / 86400);
    if (interval >= 1) {
        return interval + " day" + (interval > 1 ? "s" : "") + " ago";
    }
    interval = Math.floor(seconds / 3600);
    if (interval >= 1) {
        return interval + " hour" + (interval > 1 ? "s" : "") + " ago";
    }
    interval = Math.floor(seconds / 60);
    if (interval >= 1) {
        return interval + " minute" + (interval > 1 ? "s" : "") + " ago";
    }
    return Math.floor(seconds) + " second" + (seconds > 1 ? "s" : "") + " ago";
}
    
    async markAsRead(notificationId) {
        await fetch(`/lost_and_found/api/notifications/${notificationId}/read`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });
        
        if (this.unreadCount > 0) {
            this.unreadCount--;
            this.updateBadge();
        }
    }
    
    async markAllAsRead() {
        await fetch('/lost_and_found/api/notifications/read_all', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });
        
        this.unreadCount = 0;
        this.updateBadge();
        await this.loadNotifications();
    }
    
    startPolling() {
        // Poll every 30 seconds
        setInterval(() => this.loadNotifications(), 30000);
    }
}
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        if (document.getElementById('notificationDropdown')) {
            window.notificationManager = new NotificationManager();
        }
    }, 100);
});