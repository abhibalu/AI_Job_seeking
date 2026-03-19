export function formatTimeAgo(dateString: string | null | undefined): string {
    if (!dateString) return '';

    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    const days = seconds / 86400;

    // > 7 days: show date (e.g. "Mar 12" or "Mar 12, 2024" if different year)
    if (days > 7) {
        const sameYear = date.getFullYear() === now.getFullYear();
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            ...(sameYear ? {} : { year: 'numeric' }),
        });
    }

    if (days > 1) return Math.floor(days) + "d ago";

    const hours = seconds / 3600;
    if (hours > 1) return Math.floor(hours) + "h ago";

    const minutes = seconds / 60;
    if (minutes > 1) return Math.floor(minutes) + "m ago";

    return "just now";
}
