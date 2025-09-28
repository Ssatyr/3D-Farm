"""Initial database setup

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create printers table
    op.create_table('printers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('serial_no', sa.String(), nullable=False),
        sa.Column('machine_name', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('model', sa.String(), nullable=True),
        sa.Column('max_bed_temp', sa.Float(), nullable=True),
        sa.Column('max_nozzle_temp', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_printers_id'), 'printers', ['id'], unique=False)
    op.create_index(op.f('ix_printers_serial_no'), 'printers', ['serial_no'], unique=True)

    # Create print_jobs table
    op.create_table('print_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.String(), nullable=False),
        sa.Column('printer_id', sa.Integer(), nullable=False),
        sa.Column('part_name', sa.String(), nullable=False),
        sa.Column('part_description', sa.Text(), nullable=True),
        sa.Column('batch', sa.String(), nullable=True),
        sa.Column('operator', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('estimated_time_min', sa.Integer(), nullable=True),
        sa.Column('actual_time_min', sa.Integer(), nullable=True),
        sa.Column('material_g', sa.Float(), nullable=True),
        sa.Column('spool_id', sa.String(), nullable=True),
        sa.Column('progress_percentage', sa.Float(), nullable=True),
        sa.Column('current_layer', sa.Integer(), nullable=True),
        sa.Column('total_layers', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['printer_id'], ['printers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_print_jobs_id'), 'print_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_print_jobs_job_id'), 'print_jobs', ['job_id'], unique=True)

    # Create failure_events table
    op.create_table('failure_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('failure_type', sa.String(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('image_path', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['print_jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_failure_events_id'), 'failure_events', ['id'], unique=False)

    # Create spools table
    op.create_table('spools',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('spool_id', sa.String(), nullable=False),
        sa.Column('material_type', sa.String(), nullable=False),
        sa.Column('color', sa.String(), nullable=True),
        sa.Column('brand', sa.String(), nullable=True),
        sa.Column('total_weight_g', sa.Float(), nullable=False),
        sa.Column('remaining_weight_g', sa.Float(), nullable=False),
        sa.Column('usage_percentage', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_low_inventory', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_spools_id'), 'spools', ['id'], unique=False)
    op.create_index(op.f('ix_spools_spool_id'), 'spools', ['spool_id'], unique=True)

    # Create inventory_alerts table
    op.create_table('inventory_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('spool_id', sa.String(), nullable=False),
        sa.Column('alert_type', sa.String(), nullable=False),
        sa.Column('threshold_percentage', sa.Float(), nullable=False),
        sa.Column('current_percentage', sa.Float(), nullable=False),
        sa.Column('message', sa.String(), nullable=False),
        sa.Column('is_resolved', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inventory_alerts_id'), 'inventory_alerts', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_inventory_alerts_id'), table_name='inventory_alerts')
    op.drop_table('inventory_alerts')
    op.drop_index(op.f('ix_spools_spool_id'), table_name='spools')
    op.drop_index(op.f('ix_spools_id'), table_name='spools')
    op.drop_table('spools')
    op.drop_index(op.f('ix_failure_events_id'), table_name='failure_events')
    op.drop_table('failure_events')
    op.drop_index(op.f('ix_print_jobs_job_id'), table_name='print_jobs')
    op.drop_index(op.f('ix_print_jobs_id'), table_name='print_jobs')
    op.drop_table('print_jobs')
    op.drop_index(op.f('ix_printers_serial_no'), table_name='printers')
    op.drop_index(op.f('ix_printers_id'), table_name='printers')
    op.drop_table('printers')
