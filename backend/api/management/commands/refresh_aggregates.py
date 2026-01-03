"""
Management command to refresh pre-aggregated statistics tables.
Run every 15 minutes via Task Scheduler to keep dashboard/analytics fast.

Usage:
    python manage.py refresh_aggregates
    python manage.py refresh_aggregates --dry-run
    python manage.py refresh_aggregates --date 2025-12-31
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q, Case, When, F
from django.db.models.functions import Coalesce
from datetime import timedelta
import logging

from api.models import (
    Ticket, User, Product, Department,
    DailyStatistics, UserPerformanceSnapshot, ProductSnapshot, DepartmentSnapshot,
    TicketProductItem
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Refresh pre-aggregated statistics tables for dashboard and analytics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Calculate stats but do not save to database'
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Specific date to refresh (YYYY-MM-DD format). Default: today'
        )
        parser.add_argument(
            '--all-dates',
            action='store_true',
            help='Refresh stats for all dates with ticket activity'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        specific_date = options.get('date')
        all_dates = options.get('all_dates')

        if specific_date:
            from datetime import datetime
            target_date = datetime.strptime(specific_date, '%Y-%m-%d').date()
            dates_to_refresh = [target_date]
        elif all_dates:
            # Get all unique dates from tickets
            dates_to_refresh = list(
                Ticket.objects.filter(is_deleted=False)
                .values_list('created_at__date', flat=True)
                .distinct()
            )
            self.stdout.write(f"Found {len(dates_to_refresh)} dates to refresh")
        else:
            target_date = timezone.now().date()
            dates_to_refresh = [target_date]

        for target_date in dates_to_refresh:
            self.refresh_date(target_date, dry_run)

        if not dry_run:
            self.stdout.write(self.style.SUCCESS('Aggregates refreshed successfully!'))
        else:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes saved'))

    def refresh_date(self, target_date, dry_run):
        """Refresh all statistics for a specific date"""
        self.stdout.write(f"Refreshing stats for {target_date}...")

        # Get base queryset - all active tickets
        all_tickets = Ticket.objects.filter(is_deleted=False)

        # 1. DAILY STATISTICS
        daily_stats = self.calculate_daily_stats(all_tickets, target_date)
        if not dry_run:
            DailyStatistics.objects.update_or_create(
                date=target_date,
                defaults=daily_stats
            )
        self.stdout.write(f"  Daily stats: {daily_stats['total_tickets']} tickets, "
                          f"{daily_stats['tickets_completed']} completed")

        # 2. USER PERFORMANCE SNAPSHOTS
        users = User.objects.filter(role__in=['member', 'admin'])
        for user in users:
            user_stats = self.calculate_user_stats(user, all_tickets, target_date)
            if user_stats['assigned_count'] > 0 or user_stats['completed_count'] > 0:
                if not dry_run:
                    UserPerformanceSnapshot.objects.update_or_create(
                        user=user,
                        date=target_date,
                        defaults=user_stats
                    )
        self.stdout.write(f"  User snapshots: {users.count()} users processed")

        # 3. PRODUCT SNAPSHOTS
        products = Product.objects.filter(is_active=True)
        for product in products:
            product_stats = self.calculate_product_stats(product, all_tickets, target_date)
            if product_stats['ticket_count'] > 0:
                if not dry_run:
                    ProductSnapshot.objects.update_or_create(
                        product=product,
                        date=target_date,
                        defaults=product_stats
                    )
        self.stdout.write(f"  Product snapshots: {products.count()} products processed")

        # 4. DEPARTMENT SNAPSHOTS
        departments = Department.objects.filter(is_active=True)
        for dept in departments:
            dept_stats = self.calculate_department_stats(dept, all_tickets, target_date)
            if dept_stats['ticket_count'] > 0:
                if not dry_run:
                    DepartmentSnapshot.objects.update_or_create(
                        department=dept,
                        date=target_date,
                        defaults=dept_stats
                    )
        self.stdout.write(f"  Department snapshots: {departments.count()} departments processed")

    def calculate_daily_stats(self, all_tickets, target_date):
        """Calculate daily aggregate statistics"""
        now = timezone.now()

        # Basic counts using single aggregate query
        counts = all_tickets.aggregate(
            total=Count('id'),
            pending_dept=Count(Case(When(status=Ticket.Status.REQUESTED, then=1))),
            pending_creative=Count(Case(When(status=Ticket.Status.PENDING_CREATIVE, then=1))),
            approved=Count(Case(When(status=Ticket.Status.APPROVED, then=1))),
            in_progress=Count(Case(When(status=Ticket.Status.IN_PROGRESS, then=1))),
            completed=Count(Case(When(status=Ticket.Status.COMPLETED, then=1))),
            rejected=Count(Case(When(status=Ticket.Status.REJECTED, then=1))),
            urgent=Count(Case(When(priority=Ticket.Priority.URGENT, then=1))),
            high=Count(Case(When(priority=Ticket.Priority.HIGH, then=1))),
            medium=Count(Case(When(priority=Ticket.Priority.MEDIUM, then=1))),
            low=Count(Case(When(priority=Ticket.Priority.LOW, then=1))),
        )

        # Overdue count
        overdue_count = all_tickets.filter(
            deadline__lt=now,
            status__in=[Ticket.Status.APPROVED, Ticket.Status.IN_PROGRESS]
        ).count()

        # Tickets created/completed on this date
        tickets_created = all_tickets.filter(created_at__date=target_date).count()
        tickets_completed = all_tickets.filter(
            status=Ticket.Status.COMPLETED,
            completed_at__date=target_date
        ).count()

        # Output quantities
        completed_tickets = all_tickets.filter(status=Ticket.Status.COMPLETED)

        # Regular ticket quantities
        regular_qty = completed_tickets.exclude(
            request_type__in=['ads', 'telegram_channel']
        ).aggregate(
            total=Coalesce(Sum('quantity'), 0),
            video=Coalesce(Sum(Case(When(criteria='video', then='quantity'))), 0),
            image=Coalesce(Sum(Case(When(criteria='image', then='quantity'))), 0)
        )

        # Ads/Telegram product items
        product_items_qty = TicketProductItem.objects.filter(
            ticket__status=Ticket.Status.COMPLETED,
            ticket__is_deleted=False
        ).aggregate(
            total=Coalesce(Sum('quantity'), 0),
            video=Coalesce(Sum(Case(When(criteria='video', then='quantity'))), 0),
            image=Coalesce(Sum(Case(When(criteria='image', then='quantity'))), 0)
        )

        total_quantity = (regular_qty['total'] or 0) + (product_items_qty['total'] or 0)
        video_quantity = (regular_qty['video'] or 0) + (product_items_qty['video'] or 0)
        image_quantity = (regular_qty['image'] or 0) + (product_items_qty['image'] or 0)

        # Time metrics from completed tickets
        time_metrics = completed_tickets.filter(
            started_at__isnull=False,
            completed_at__isnull=False
        ).aggregate(
            avg_processing=Avg(F('completed_at') - F('started_at'))
        )

        avg_processing_seconds = 0
        if time_metrics['avg_processing']:
            avg_processing_seconds = time_metrics['avg_processing'].total_seconds()

        # Acknowledge time from analytics
        from api.models import TicketAnalytics
        ack_metrics = TicketAnalytics.objects.filter(
            ticket__is_deleted=False,
            time_to_acknowledge__isnull=False
        ).aggregate(avg_ack=Avg('time_to_acknowledge'))
        avg_acknowledge_seconds = ack_metrics['avg_ack'] or 0

        # Completion rate
        assigned_count = all_tickets.filter(assigned_to__isnull=False).count()
        completed_count = counts['completed'] or 0
        completion_rate = (completed_count / assigned_count * 100) if assigned_count > 0 else 0

        # Revision stats
        tickets_with_revisions = all_tickets.filter(revision_count__gt=0).count()
        total_revisions = all_tickets.aggregate(total=Sum('revision_count'))['total'] or 0

        return {
            'total_tickets': counts['total'] or 0,
            'tickets_created': tickets_created,
            'tickets_completed': tickets_completed,
            'tickets_in_progress': counts['in_progress'] or 0,
            'tickets_pending_dept': counts['pending_dept'] or 0,
            'tickets_pending_creative': counts['pending_creative'] or 0,
            'tickets_approved': counts['approved'] or 0,
            'tickets_rejected': counts['rejected'] or 0,
            'tickets_overdue': overdue_count,
            'urgent_count': counts['urgent'] or 0,
            'high_count': counts['high'] or 0,
            'medium_count': counts['medium'] or 0,
            'low_count': counts['low'] or 0,
            'total_quantity': total_quantity,
            'video_quantity': video_quantity,
            'image_quantity': image_quantity,
            'avg_processing_seconds': avg_processing_seconds,
            'avg_acknowledge_seconds': avg_acknowledge_seconds,
            'completion_rate': completion_rate,
            'tickets_with_revisions': tickets_with_revisions,
            'total_revisions': total_revisions,
        }

    def calculate_user_stats(self, user, all_tickets, target_date):
        """Calculate per-user performance statistics"""
        user_tickets = all_tickets.filter(
            Q(assigned_to=user) | Q(collaborators__user=user)
        ).distinct()

        assigned_count = user_tickets.count()
        completed_tickets = user_tickets.filter(status=Ticket.Status.COMPLETED)
        completed_count = completed_tickets.count()
        in_progress_count = user_tickets.filter(status=Ticket.Status.IN_PROGRESS).count()

        # Quantities
        assigned_qty = user_tickets.aggregate(
            total=Coalesce(Sum('quantity'), 0)
        )['total'] or 0

        output_qty = completed_tickets.aggregate(
            total=Coalesce(Sum('quantity'), 0)
        )['total'] or 0

        # Add product items for Ads/Telegram
        assigned_items_qty = TicketProductItem.objects.filter(
            ticket__in=user_tickets
        ).aggregate(total=Coalesce(Sum('quantity'), 0))['total'] or 0

        output_items_qty = TicketProductItem.objects.filter(
            ticket__in=completed_tickets
        ).aggregate(total=Coalesce(Sum('quantity'), 0))['total'] or 0

        assigned_quantity = assigned_qty + assigned_items_qty
        output_quantity = output_qty + output_items_qty

        # Completion rate
        completion_rate = (completed_count / assigned_count * 100) if assigned_count > 0 else 0

        # Time metrics
        time_metrics = completed_tickets.filter(
            started_at__isnull=False,
            completed_at__isnull=False
        ).aggregate(
            avg_processing=Avg(F('completed_at') - F('started_at'))
        )

        avg_processing_seconds = 0
        if time_metrics['avg_processing']:
            avg_processing_seconds = time_metrics['avg_processing'].total_seconds()

        # Acknowledge time
        from api.models import TicketAnalytics
        ack_metrics = TicketAnalytics.objects.filter(
            ticket__in=user_tickets,
            time_to_acknowledge__isnull=False
        ).aggregate(avg_ack=Avg('time_to_acknowledge'))
        avg_acknowledge_seconds = ack_metrics['avg_ack'] or 0

        return {
            'assigned_count': assigned_count,
            'assigned_quantity': assigned_quantity,
            'completed_count': completed_count,
            'output_quantity': output_quantity,
            'in_progress_count': in_progress_count,
            'completion_rate': completion_rate,
            'avg_processing_seconds': avg_processing_seconds,
            'avg_acknowledge_seconds': avg_acknowledge_seconds,
            'avg_video_time_seconds': 0,  # TODO: Calculate from analytics
            'avg_image_time_seconds': 0,  # TODO: Calculate from analytics
        }

    def calculate_product_stats(self, product, all_tickets, target_date):
        """Calculate per-product statistics"""
        product_tickets = all_tickets.filter(ticket_product=product)

        ticket_count = product_tickets.count()
        completed_count = product_tickets.filter(status=Ticket.Status.COMPLETED).count()
        in_progress_count = product_tickets.filter(status=Ticket.Status.IN_PROGRESS).count()

        # Quantities
        total_quantity = product_tickets.aggregate(
            total=Coalesce(Sum('quantity'), 0)
        )['total'] or 0

        completed_quantity = product_tickets.filter(
            status=Ticket.Status.COMPLETED
        ).aggregate(
            total=Coalesce(Sum('quantity'), 0)
        )['total'] or 0

        return {
            'ticket_count': ticket_count,
            'total_quantity': total_quantity,
            'completed_count': completed_count,
            'completed_quantity': completed_quantity,
            'in_progress_count': in_progress_count,
        }

    def calculate_department_stats(self, department, all_tickets, target_date):
        """Calculate per-department statistics"""
        dept_tickets = all_tickets.filter(target_department=department)

        ticket_count = dept_tickets.count()
        completed_count = dept_tickets.filter(status=Ticket.Status.COMPLETED).count()
        in_progress_count = dept_tickets.filter(status=Ticket.Status.IN_PROGRESS).count()

        # Quantities
        total_quantity = dept_tickets.aggregate(
            total=Coalesce(Sum('quantity'), 0)
        )['total'] or 0

        completed_quantity = dept_tickets.filter(
            status=Ticket.Status.COMPLETED
        ).aggregate(
            total=Coalesce(Sum('quantity'), 0)
        )['total'] or 0

        return {
            'ticket_count': ticket_count,
            'total_quantity': total_quantity,
            'completed_count': completed_count,
            'completed_quantity': completed_quantity,
            'in_progress_count': in_progress_count,
        }
