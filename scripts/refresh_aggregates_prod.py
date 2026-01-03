"""
Refresh aggregate statistics tables for production database.
Run via Windows Task Scheduler every 15 minutes.
"""

import psycopg2
from datetime import datetime

# Production database connection
DATABASE_URL = "postgresql://postgres:UpMenlbgyXgxiqzIYPbggoPZxtBjbaAs@switchback.proxy.rlwy.net:49452/railway"

def refresh_daily_statistics(cursor):
    """Refresh DailyStatistics table"""
    cursor.execute("""
        INSERT INTO api_dailystatistics (
            date, total_tickets, tickets_created, tickets_completed, tickets_in_progress,
            tickets_pending_dept, tickets_pending_creative, tickets_approved, tickets_rejected,
            tickets_overdue, urgent_count, high_count, medium_count, low_count,
            total_quantity, video_quantity, image_quantity, avg_processing_seconds,
            avg_acknowledge_seconds, avg_video_time_seconds, avg_image_time_seconds,
            completion_rate, tickets_with_revisions, total_revisions, last_updated
        )
        SELECT
            CURRENT_DATE,
            COUNT(*),
            COUNT(*) FILTER (WHERE created_at::date = CURRENT_DATE),
            COUNT(*) FILTER (WHERE status = 'completed' AND completed_at::date = CURRENT_DATE),
            COUNT(*) FILTER (WHERE status = 'in_progress'),
            COUNT(*) FILTER (WHERE status = 'requested'),
            COUNT(*) FILTER (WHERE status = 'pending_creative'),
            COUNT(*) FILTER (WHERE status = 'approved'),
            COUNT(*) FILTER (WHERE status = 'rejected'),
            COUNT(*) FILTER (WHERE deadline < NOW() AND status IN ('approved', 'in_progress')),
            COUNT(*) FILTER (WHERE priority = 'urgent'),
            COUNT(*) FILTER (WHERE priority = 'high'),
            COUNT(*) FILTER (WHERE priority = 'medium'),
            COUNT(*) FILTER (WHERE priority = 'low'),
            COALESCE(SUM(quantity), 0),
            COALESCE(SUM(CASE WHEN criteria = 'video' THEN quantity ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN criteria = 'image' THEN quantity ELSE 0 END), 0),
            COALESCE(AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) FILTER (WHERE completed_at IS NOT NULL AND started_at IS NOT NULL), 0),
            0, 0, 0,
            CASE WHEN COUNT(*) FILTER (WHERE assigned_to_id IS NOT NULL) > 0
                THEN (COUNT(*) FILTER (WHERE status = 'completed')::float / COUNT(*) FILTER (WHERE assigned_to_id IS NOT NULL) * 100)
                ELSE 0 END,
            COUNT(*) FILTER (WHERE revision_count > 0),
            COALESCE(SUM(revision_count), 0),
            NOW()
        FROM api_ticket WHERE is_deleted = false
        ON CONFLICT (date) DO UPDATE SET
            total_tickets = EXCLUDED.total_tickets,
            tickets_created = EXCLUDED.tickets_created,
            tickets_completed = EXCLUDED.tickets_completed,
            tickets_in_progress = EXCLUDED.tickets_in_progress,
            tickets_pending_dept = EXCLUDED.tickets_pending_dept,
            tickets_pending_creative = EXCLUDED.tickets_pending_creative,
            tickets_approved = EXCLUDED.tickets_approved,
            tickets_rejected = EXCLUDED.tickets_rejected,
            tickets_overdue = EXCLUDED.tickets_overdue,
            urgent_count = EXCLUDED.urgent_count,
            high_count = EXCLUDED.high_count,
            medium_count = EXCLUDED.medium_count,
            low_count = EXCLUDED.low_count,
            total_quantity = EXCLUDED.total_quantity,
            video_quantity = EXCLUDED.video_quantity,
            image_quantity = EXCLUDED.image_quantity,
            avg_processing_seconds = EXCLUDED.avg_processing_seconds,
            completion_rate = EXCLUDED.completion_rate,
            tickets_with_revisions = EXCLUDED.tickets_with_revisions,
            total_revisions = EXCLUDED.total_revisions,
            last_updated = NOW()
    """)

def refresh_user_snapshots(cursor):
    """Refresh UserPerformanceSnapshot table"""
    cursor.execute("""
        INSERT INTO api_userperformancesnapshot (
            user_id, date, assigned_count, assigned_quantity, completed_count, output_quantity,
            in_progress_count, completion_rate, avg_processing_seconds, avg_acknowledge_seconds,
            avg_video_time_seconds, avg_image_time_seconds, last_updated
        )
        SELECT
            u.id,
            CURRENT_DATE,
            COUNT(DISTINCT t.id) FILTER (WHERE t.assigned_to_id = u.id),
            COALESCE(SUM(t.quantity) FILTER (WHERE t.assigned_to_id = u.id), 0),
            COUNT(DISTINCT t.id) FILTER (WHERE t.assigned_to_id = u.id AND t.status = 'completed'),
            COALESCE(SUM(t.quantity) FILTER (WHERE t.assigned_to_id = u.id AND t.status = 'completed'), 0),
            COUNT(DISTINCT t.id) FILTER (WHERE t.assigned_to_id = u.id AND t.status = 'in_progress'),
            CASE WHEN COUNT(DISTINCT t.id) FILTER (WHERE t.assigned_to_id = u.id) > 0
                THEN (COUNT(DISTINCT t.id) FILTER (WHERE t.assigned_to_id = u.id AND t.status = 'completed')::float /
                      COUNT(DISTINCT t.id) FILTER (WHERE t.assigned_to_id = u.id) * 100)
                ELSE 0 END,
            COALESCE(AVG(EXTRACT(EPOCH FROM (t.completed_at - t.started_at))) FILTER (WHERE t.assigned_to_id = u.id AND t.completed_at IS NOT NULL AND t.started_at IS NOT NULL), 0),
            0, 0, 0,
            NOW()
        FROM api_user u
        LEFT JOIN api_ticket t ON (t.assigned_to_id = u.id AND t.is_deleted = false)
        WHERE u.role IN ('member', 'admin', 'manager')
        GROUP BY u.id
        HAVING COUNT(DISTINCT t.id) > 0
        ON CONFLICT (user_id, date) DO UPDATE SET
            assigned_count = EXCLUDED.assigned_count,
            assigned_quantity = EXCLUDED.assigned_quantity,
            completed_count = EXCLUDED.completed_count,
            output_quantity = EXCLUDED.output_quantity,
            in_progress_count = EXCLUDED.in_progress_count,
            completion_rate = EXCLUDED.completion_rate,
            avg_processing_seconds = EXCLUDED.avg_processing_seconds,
            last_updated = NOW()
    """)

def refresh_product_snapshots(cursor):
    """Refresh ProductSnapshot table"""
    cursor.execute("""
        INSERT INTO api_productsnapshot (
            product_id, date, ticket_count, total_quantity, completed_count, completed_quantity, in_progress_count, last_updated
        )
        SELECT
            p.id,
            CURRENT_DATE,
            COUNT(t.id),
            COALESCE(SUM(t.quantity), 0),
            COUNT(t.id) FILTER (WHERE t.status = 'completed'),
            COALESCE(SUM(t.quantity) FILTER (WHERE t.status = 'completed'), 0),
            COUNT(t.id) FILTER (WHERE t.status = 'in_progress'),
            NOW()
        FROM api_product p
        LEFT JOIN api_ticket t ON (t.ticket_product_id = p.id AND t.is_deleted = false)
        WHERE p.is_active = true
        GROUP BY p.id
        HAVING COUNT(t.id) > 0
        ON CONFLICT (product_id, date) DO UPDATE SET
            ticket_count = EXCLUDED.ticket_count,
            total_quantity = EXCLUDED.total_quantity,
            completed_count = EXCLUDED.completed_count,
            completed_quantity = EXCLUDED.completed_quantity,
            in_progress_count = EXCLUDED.in_progress_count,
            last_updated = NOW()
    """)

def refresh_department_snapshots(cursor):
    """Refresh DepartmentSnapshot table"""
    cursor.execute("""
        INSERT INTO api_departmentsnapshot (
            department_id, date, ticket_count, total_quantity, completed_count, completed_quantity, in_progress_count, last_updated
        )
        SELECT
            d.id,
            CURRENT_DATE,
            COUNT(t.id),
            COALESCE(SUM(t.quantity), 0),
            COUNT(t.id) FILTER (WHERE t.status = 'completed'),
            COALESCE(SUM(t.quantity) FILTER (WHERE t.status = 'completed'), 0),
            COUNT(t.id) FILTER (WHERE t.status = 'in_progress'),
            NOW()
        FROM api_department d
        LEFT JOIN api_ticket t ON (t.target_department_id = d.id AND t.is_deleted = false)
        WHERE d.is_active = true
        GROUP BY d.id
        HAVING COUNT(t.id) > 0
        ON CONFLICT (department_id, date) DO UPDATE SET
            ticket_count = EXCLUDED.ticket_count,
            total_quantity = EXCLUDED.total_quantity,
            completed_count = EXCLUDED.completed_count,
            completed_quantity = EXCLUDED.completed_quantity,
            in_progress_count = EXCLUDED.in_progress_count,
            last_updated = NOW()
    """)

def main():
    print(f"[{datetime.now()}] Starting refresh_aggregates...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        refresh_daily_statistics(cursor)
        print("  - DailyStatistics refreshed")

        refresh_user_snapshots(cursor)
        print("  - UserPerformanceSnapshot refreshed")

        refresh_product_snapshots(cursor)
        print("  - ProductSnapshot refreshed")

        refresh_department_snapshots(cursor)
        print("  - DepartmentSnapshot refreshed")

        conn.commit()
        cursor.close()
        conn.close()

        print(f"[{datetime.now()}] Refresh completed successfully!")

    except Exception as e:
        print(f"[{datetime.now()}] ERROR: {e}")
        raise

if __name__ == "__main__":
    main()
