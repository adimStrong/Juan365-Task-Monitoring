#!/usr/bin/env python
"""
Monthly Report Generator CLI

Generates comprehensive monthly KPI reports for the Creative Team.
Can output in multiple formats: JSON, formatted text, or Telegram-ready markdown.

Usage:
    python generate_monthly_report.py --year 2026 --month 1 --format text
    python generate_monthly_report.py --year 2026 --month 1 --format telegram
    python generate_monthly_report.py --year 2026 --month 1 --format json --output report.json

Options:
    --year      Report year (default: current year)
    --month     Report month 1-12 (default: current month)
    --format    Output format: json, text, telegram (default: text)
    --output    Output file path (default: stdout)
"""

import os
import sys
import json
import argparse
from datetime import datetime
from calendar import monthrange
import calendar

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ticketing.settings')

import django
django.setup()

from django.db.models import Sum
from django.utils import timezone
from api.models import Ticket, User, TicketProductItem, TicketCollaborator


def get_rag_emoji(status):
    """Return emoji for RAG status"""
    return {
        'green': '\u2705',   # Green check
        'amber': '\u26A0\uFE0F',   # Warning
        'red': '\u274C',     # Red X
        'blue': '\u2139\uFE0F',    # Info
        'grey': '\u2B55',    # Circle
    }.get(status, '\u2B55')


def get_rag_status(value, thresholds, higher_is_better=True):
    """Calculate RAG status based on thresholds"""
    if value is None:
        return {'status': 'grey', 'label': 'N/A'}
    if higher_is_better:
        if value >= thresholds['green']:
            return {'status': 'green', 'label': 'On Track'}
        elif value >= thresholds['amber']:
            return {'status': 'amber', 'label': 'At Risk'}
        else:
            return {'status': 'red', 'label': 'Off Track'}
    else:
        if value <= thresholds['green']:
            return {'status': 'green', 'label': 'On Track'}
        elif value <= thresholds['amber']:
            return {'status': 'amber', 'label': 'At Risk'}
        else:
            return {'status': 'red', 'label': 'Off Track'}


def get_brand(product_name):
    """Map product name to brand"""
    name_upper = (product_name or '').upper()
    if 'LIVESTREAM' in name_upper or 'LIVE STREAM' in name_upper:
        return 'Juan365 Live Stream'
    elif 'STUDIOS' in name_upper or 'STUDIO' in name_upper:
        return 'Juan Studio'
    elif 'JUANBINGO' in name_upper or 'JUAN BINGO' in name_upper:
        return 'Juan Bingo'
    elif 'JUANSPORTS' in name_upper or 'JUAN SPORTS' in name_upper:
        return 'JuanSports'
    elif '759' in name_upper or 'GAMING' in name_upper:
        return '759 Gaming'
    elif 'JUAN365' in name_upper or 'DIGIADS' in name_upper or 'DIGI ADS' in name_upper:
        return 'Juan365'
    else:
        return product_name


def generate_report_data(year, month):
    """Generate the report data dictionary"""
    # Calculate date range for the month
    _, last_day = monthrange(year, month)
    date_from = f"{year}-{month:02d}-01"
    date_to = f"{year}-{month:02d}-{last_day:02d}"
    month_name = calendar.month_name[month]

    # Calculate previous month for MoM comparison
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    _, prev_last_day = monthrange(prev_year, prev_month)
    prev_date_from = f"{prev_year}-{prev_month:02d}-01"
    prev_date_to = f"{prev_year}-{prev_month:02d}-{prev_last_day:02d}"
    prev_month_name = calendar.month_name[prev_month]

    # Current month data
    tickets = Ticket.objects.select_related(
        'analytics', 'assigned_to', 'target_department', 'ticket_product'
    ).filter(
        is_deleted=False,
        created_at__date__gte=date_from,
        created_at__date__lte=date_to
    )
    tickets_list = list(tickets)

    # Basic counts
    total_tickets = len(tickets_list)
    assigned_tickets = sum(1 for t in tickets_list if t.assigned_to_id is not None)
    completed_tickets = sum(1 for t in tickets_list if t.status == Ticket.Status.COMPLETED)
    in_progress_tickets = sum(1 for t in tickets_list if t.status == Ticket.Status.IN_PROGRESS)

    # Completion rate
    completion_rate = round(completed_tickets / assigned_tickets * 100, 1) if assigned_tickets > 0 else 0

    # On-time rate
    completed_list = [t for t in tickets_list if t.status == Ticket.Status.COMPLETED]
    on_time_tickets = sum(
        1 for t in completed_list
        if t.deadline and t.completed_at and t.completed_at <= t.deadline
    )
    tickets_with_deadline = sum(1 for t in completed_list if t.deadline)
    on_time_rate = round(on_time_tickets / tickets_with_deadline * 100, 1) if tickets_with_deadline > 0 else None

    # Overdue metrics
    now = timezone.now()
    active_tickets = [t for t in tickets_list if t.status not in [Ticket.Status.COMPLETED, Ticket.Status.REJECTED]]
    overdue_tickets = [t for t in active_tickets if t.deadline and now > t.deadline]
    overdue_count = len(overdue_tickets)
    overdue_rate = round(overdue_count / len(active_tickets) * 100, 1) if active_tickets else 0

    # Revision statistics
    revision_counts = [t.revision_count or 0 for t in completed_list]
    total_revisions = sum(revision_counts)
    avg_revisions = round(total_revisions / len(completed_list), 2) if completed_list else 0

    # Revision distribution
    revision_distribution = {
        '0': sum(1 for r in revision_counts if r == 0),
        '1': sum(1 for r in revision_counts if r == 1),
        '2': sum(1 for r in revision_counts if r == 2),
        '3': sum(1 for r in revision_counts if r == 3),
        '4+': sum(1 for r in revision_counts if r >= 4),
    }

    # Total output
    regular_quantity = sum(
        t.quantity or 0 for t in completed_list
        if t.request_type not in ['ads', 'telegram_channel']
    )
    completed_ids = [t.id for t in completed_list]
    product_items_quantity = TicketProductItem.objects.filter(
        ticket_id__in=completed_ids
    ).aggregate(total=Sum('quantity'))['total'] or 0
    total_output = regular_quantity + product_items_quantity

    # Video/Image breakdown
    product_items_list = list(TicketProductItem.objects.filter(
        ticket_id__in=completed_ids
    ).select_related('product', 'ticket'))

    video_quantity = sum(t.quantity or 0 for t in completed_list if t.criteria == 'video')
    video_quantity += sum(
        p.quantity or 0 for p in product_items_list
        if p.product and 'VID' in (p.product.name or '').upper()
    )

    image_quantity = sum(t.quantity or 0 for t in completed_list if t.criteria == 'image')
    image_quantity += sum(
        p.quantity or 0 for p in product_items_list
        if p.product and 'STATIC' in (p.product.name or '').upper()
    )

    # KPI Summary with RAG
    kpi_summary = {
        'completion_rate': {
            'value': completion_rate,
            'target': 80,
            'unit': '%',
            'rag': get_rag_status(completion_rate, {'green': 80, 'amber': 70}),
        },
        'on_time_rate': {
            'value': on_time_rate,
            'target': 80,
            'unit': '%',
            'rag': get_rag_status(on_time_rate, {'green': 80, 'amber': 70}) if on_time_rate is not None else {'status': 'grey', 'label': 'N/A'},
        },
        'avg_revisions': {
            'value': avg_revisions,
            'target': 3,
            'unit': '',
            'rag': get_rag_status(avg_revisions, {'green': 3, 'amber': 4}, higher_is_better=False),
        },
        'total_output': {
            'value': total_output,
            'target': None,
            'unit': 'creatives',
            'rag': {'status': 'blue', 'label': 'Info'},
        },
        'overdue_rate': {
            'value': overdue_rate,
            'target': 5,
            'unit': '%',
            'rag': get_rag_status(overdue_rate, {'green': 5, 'amber': 10}, higher_is_better=False),
        },
    }

    # Team leaderboard
    tickets_by_user = {}
    for t in tickets_list:
        if t.assigned_to_id:
            if t.assigned_to_id not in tickets_by_user:
                tickets_by_user[t.assigned_to_id] = set()
            tickets_by_user[t.assigned_to_id].add(t.id)

    ticket_ids = [t.id for t in tickets_list]
    collaborators = TicketCollaborator.objects.filter(ticket_id__in=ticket_ids).values('user_id', 'ticket_id')
    for collab in collaborators:
        user_id = collab['user_id']
        if user_id not in tickets_by_user:
            tickets_by_user[user_id] = set()
        tickets_by_user[user_id].add(collab['ticket_id'])

    tickets_dict = {t.id: t for t in tickets_list}
    users_with_tickets = User.objects.select_related('user_department').filter(id__in=tickets_by_user.keys())

    leaderboard = []
    for user in users_with_tickets:
        user_ticket_ids = tickets_by_user.get(user.id, set())
        user_tickets = [tickets_dict[tid] for tid in user_ticket_ids if tid in tickets_dict]
        user_completed = [t for t in user_tickets if t.status == Ticket.Status.COMPLETED]

        user_regular_qty = sum(
            t.quantity or 0 for t in user_completed
            if t.request_type not in ['ads', 'telegram_channel']
        )
        user_completed_ids = [t.id for t in user_completed]
        user_product_qty = TicketProductItem.objects.filter(
            ticket_id__in=user_completed_ids
        ).aggregate(total=Sum('quantity'))['total'] or 0
        user_output = user_regular_qty + user_product_qty

        user_on_time = sum(
            1 for t in user_completed
            if t.deadline and t.completed_at and t.completed_at <= t.deadline
        )
        user_with_deadline = sum(1 for t in user_completed if t.deadline)
        user_on_time_rate = round(user_on_time / user_with_deadline * 100, 1) if user_with_deadline > 0 else None

        user_revisions = [t.revision_count or 0 for t in user_completed]
        user_avg_revisions = round(sum(user_revisions) / len(user_revisions), 2) if user_revisions else 0

        leaderboard.append({
            'user_id': user.id,
            'username': user.username,
            'full_name': f"{user.first_name} {user.last_name}".strip() or user.username,
            'tickets_assigned': len(user_tickets),
            'tickets_completed': len(user_completed),
            'total_output': user_output,
            'completion_rate': round(len(user_completed) / len(user_tickets) * 100, 1) if user_tickets else 0,
            'on_time_rate': user_on_time_rate,
            'avg_revisions': user_avg_revisions,
        })

    leaderboard.sort(key=lambda x: x['total_output'], reverse=True)
    for i, item in enumerate(leaderboard):
        item['rank'] = i + 1

    # Product breakdown
    product_breakdown = {}
    for t in tickets_list:
        brand = get_brand(t.ticket_product.name if t.ticket_product else t.product)
        if brand:
            if brand not in product_breakdown:
                product_breakdown[brand] = {'count': 0, 'completed': 0, 'output': 0}
            product_breakdown[brand]['count'] += 1
            if t.status == Ticket.Status.COMPLETED:
                product_breakdown[brand]['completed'] += 1
                if t.request_type not in ['ads', 'telegram_channel']:
                    product_breakdown[brand]['output'] += t.quantity or 0

    for p in product_items_list:
        brand = get_brand(p.product.name if p.product else '')
        if brand and brand in product_breakdown:
            product_breakdown[brand]['output'] += p.quantity or 0

    by_product = [
        {'product': k, **v}
        for k, v in sorted(product_breakdown.items(), key=lambda x: x[1]['output'], reverse=True)
    ]

    # MoM comparison
    prev_tickets = Ticket.objects.filter(
        is_deleted=False,
        created_at__date__gte=prev_date_from,
        created_at__date__lte=prev_date_to
    )
    prev_tickets_list = list(prev_tickets)
    prev_total = len(prev_tickets_list)
    prev_assigned = sum(1 for t in prev_tickets_list if t.assigned_to_id is not None)
    prev_completed = sum(1 for t in prev_tickets_list if t.status == Ticket.Status.COMPLETED)
    prev_completion_rate = round(prev_completed / prev_assigned * 100, 1) if prev_assigned > 0 else 0

    prev_completed_list = [t for t in prev_tickets_list if t.status == Ticket.Status.COMPLETED]
    prev_regular_qty = sum(
        t.quantity or 0 for t in prev_completed_list
        if t.request_type not in ['ads', 'telegram_channel']
    )
    prev_completed_ids = [t.id for t in prev_completed_list]
    prev_product_qty = TicketProductItem.objects.filter(
        ticket_id__in=prev_completed_ids
    ).aggregate(total=Sum('quantity'))['total'] or 0
    prev_output = prev_regular_qty + prev_product_qty

    def calc_change(current, previous):
        if previous == 0:
            return None
        return round((current - previous) / previous * 100, 1)

    mom_comparison = {
        'previous_month': f"{prev_month_name} {prev_year}",
        'current_month': f"{month_name} {year}",
        'metrics': {
            'total_output': {
                'current': total_output,
                'previous': prev_output,
                'change': calc_change(total_output, prev_output),
            },
            'completion_rate': {
                'current': completion_rate,
                'previous': prev_completion_rate,
                'change': round(completion_rate - prev_completion_rate, 1) if prev_completion_rate else None,
            },
        },
    }

    # Auto-generated insights
    insights = {'wins': [], 'improvements': [], 'action_items': []}

    if completion_rate >= 80:
        insights['wins'].append(f"Completion rate of {completion_rate}% exceeds 80% target")
    if on_time_rate and on_time_rate >= 80:
        insights['wins'].append(f"On-time delivery at {on_time_rate}% meets target")
    if avg_revisions < 2:
        insights['wins'].append(f"Low revision rate ({avg_revisions} avg) indicates high first-time quality")

    if completion_rate < 70:
        insights['improvements'].append(f"Completion rate ({completion_rate}%) below target")
    if on_time_rate and on_time_rate < 70:
        insights['improvements'].append(f"On-time rate ({on_time_rate}%) needs attention")
    if avg_revisions > 3:
        insights['improvements'].append(f"High revision rate ({avg_revisions} avg)")
    if overdue_rate > 10:
        insights['improvements'].append(f"Overdue rate ({overdue_rate}%) exceeds threshold")

    return {
        'report_period': {
            'year': year,
            'month': month,
            'month_name': month_name,
            'date_from': date_from,
            'date_to': date_to,
        },
        'executive_summary': {
            'total_tickets': total_tickets,
            'assigned_tickets': assigned_tickets,
            'completed_tickets': completed_tickets,
            'in_progress_tickets': in_progress_tickets,
            'total_output': total_output,
            'video_quantity': video_quantity,
            'image_quantity': image_quantity,
            'kpi_summary': kpi_summary,
        },
        'quality_metrics': {
            'on_time_rate': on_time_rate,
            'avg_revisions': avg_revisions,
            'revision_distribution': revision_distribution,
        },
        'overdue_metrics': {
            'overdue_count': overdue_count,
            'overdue_rate': overdue_rate,
        },
        'team_leaderboard': leaderboard,
        'breakdowns': {
            'by_product': by_product,
        },
        'mom_comparison': mom_comparison,
        'insights': insights,
    }


def format_text_report(data):
    """Format report as human-readable text"""
    lines = []
    period = data['report_period']
    summary = data['executive_summary']
    quality = data['quality_metrics']
    overdue = data['overdue_metrics']
    kpi = summary['kpi_summary']

    lines.append("=" * 60)
    lines.append(f"CREATIVE TEAM MONTHLY REPORT - {period['month_name'].upper()} {period['year']}")
    lines.append("=" * 60)
    lines.append("")

    # Executive Summary
    lines.append("EXECUTIVE SUMMARY")
    lines.append("-" * 40)
    lines.append(f"Total Tickets:     {summary['total_tickets']}")
    lines.append(f"Assigned:          {summary['assigned_tickets']}")
    lines.append(f"Completed:         {summary['completed_tickets']}")
    lines.append(f"In Progress:       {summary['in_progress_tickets']}")
    lines.append(f"Total Output:      {summary['total_output']} creatives")
    lines.append(f"  - Video:         {summary['video_quantity']}")
    lines.append(f"  - Image:         {summary['image_quantity']}")
    lines.append("")

    # KPI Summary with RAG
    lines.append("KPI SUMMARY")
    lines.append("-" * 40)
    for kpi_name, kpi_data in kpi.items():
        rag = kpi_data['rag']
        value = kpi_data['value']
        target = kpi_data['target']
        unit = kpi_data['unit']
        status_indicator = "[OK]" if rag['status'] == 'green' else "[!!]" if rag['status'] == 'red' else "[--]"
        target_str = f" (target: {target}{unit})" if target else ""
        value_str = f"{value}{unit}" if value is not None else "N/A"
        lines.append(f"  {status_indicator} {kpi_name.replace('_', ' ').title()}: {value_str}{target_str}")
    lines.append("")

    # Team Leaderboard
    lines.append("TEAM LEADERBOARD")
    lines.append("-" * 60)
    lines.append(f"{'Rank':<5} {'Designer':<20} {'Tickets':<10} {'Output':<10} {'On-Time%':<10} {'Avg Rev':<8}")
    lines.append("-" * 60)
    for member in data['team_leaderboard'][:10]:
        on_time = f"{member['on_time_rate']}%" if member['on_time_rate'] is not None else "N/A"
        lines.append(
            f"{member['rank']:<5} {member['full_name'][:18]:<20} "
            f"{member['tickets_completed']:<10} {member['total_output']:<10} "
            f"{on_time:<10} {member['avg_revisions']:<8}"
        )
    lines.append("")

    # Insights
    lines.append("INSIGHTS")
    lines.append("-" * 40)
    if data['insights']['wins']:
        lines.append("Wins:")
        for win in data['insights']['wins']:
            lines.append(f"  + {win}")
    if data['insights']['improvements']:
        lines.append("Areas for Improvement:")
        for imp in data['insights']['improvements']:
            lines.append(f"  - {imp}")
    lines.append("")

    # MoM Comparison
    mom = data['mom_comparison']
    lines.append("MONTH-OVER-MONTH COMPARISON")
    lines.append("-" * 40)
    lines.append(f"vs {mom['previous_month']}:")
    for metric, values in mom['metrics'].items():
        change = values['change']
        change_str = f"+{change}%" if change and change > 0 else f"{change}%" if change else "N/A"
        lines.append(f"  {metric.replace('_', ' ').title()}: {values['current']} ({change_str})")
    lines.append("")

    lines.append("=" * 60)
    lines.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)

    return "\n".join(lines)


def format_telegram_report(data):
    """Format report for Telegram (markdown-like format)"""
    lines = []
    period = data['report_period']
    summary = data['executive_summary']
    quality = data['quality_metrics']
    kpi = summary['kpi_summary']

    lines.append(f"*CREATIVE TEAM MONTHLY REPORT*")
    lines.append(f"*{period['month_name']} {period['year']}*")
    lines.append("")

    # Executive Summary
    lines.append("*EXECUTIVE SUMMARY*")
    lines.append(f"Total Tickets: *{summary['total_tickets']}*")
    lines.append(f"Completed: *{summary['completed_tickets']}*")
    lines.append(f"Total Output: *{summary['total_output']}* creatives")
    lines.append(f"  Video: {summary['video_quantity']} | Image: {summary['image_quantity']}")
    lines.append("")

    # KPIs with RAG emoji
    lines.append("*KEY METRICS*")
    for kpi_name, kpi_data in kpi.items():
        rag = kpi_data['rag']
        value = kpi_data['value']
        unit = kpi_data['unit']
        emoji = get_rag_emoji(rag['status'])
        value_str = f"{value}{unit}" if value is not None else "N/A"
        lines.append(f"{emoji} {kpi_name.replace('_', ' ').title()}: *{value_str}*")
    lines.append("")

    # Top 5 Performers
    lines.append("*TOP 5 PERFORMERS*")
    medals = ['\U0001F947', '\U0001F948', '\U0001F949', '4.', '5.']
    for i, member in enumerate(data['team_leaderboard'][:5]):
        lines.append(f"{medals[i]} {member['full_name']}: *{member['total_output']}* output")
    lines.append("")

    # Insights
    if data['insights']['wins']:
        lines.append("*WINS*")
        for win in data['insights']['wins']:
            lines.append(f"\u2705 {win}")
        lines.append("")

    if data['insights']['improvements']:
        lines.append("*AREAS FOR IMPROVEMENT*")
        for imp in data['insights']['improvements']:
            lines.append(f"\u26A0\uFE0F {imp}")
        lines.append("")

    # MoM
    mom = data['mom_comparison']
    lines.append("*VS PREVIOUS MONTH*")
    output_change = mom['metrics']['total_output']['change']
    if output_change:
        arrow = '\U0001F4C8' if output_change > 0 else '\U0001F4C9'
        lines.append(f"{arrow} Output: {'+' if output_change > 0 else ''}{output_change}%")
    lines.append("")

    lines.append(f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='Generate Creative Team Monthly Report')
    parser.add_argument('--year', type=int, default=datetime.now().year, help='Report year')
    parser.add_argument('--month', type=int, default=datetime.now().month, help='Report month (1-12)')
    parser.add_argument('--format', choices=['json', 'text', 'telegram'], default='text', help='Output format')
    parser.add_argument('--output', type=str, help='Output file path (default: stdout)')

    args = parser.parse_args()

    # Validate month
    if not (1 <= args.month <= 12):
        print("Error: Month must be between 1 and 12", file=sys.stderr)
        sys.exit(1)

    print(f"Generating report for {calendar.month_name[args.month]} {args.year}...", file=sys.stderr)

    # Generate report data
    data = generate_report_data(args.year, args.month)

    # Format output
    if args.format == 'json':
        output = json.dumps(data, indent=2, default=str)
    elif args.format == 'telegram':
        output = format_telegram_report(data)
    else:
        output = format_text_report(data)

    # Write output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"Report saved to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
