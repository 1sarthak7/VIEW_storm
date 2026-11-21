"""add_load_generator_nodes_and_execution_mode

Revision ID: 122b6ad9789b
Revises: e40bcd6bed30
Create Date: 2026-11-21 12:11:40.075709

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '122b6ad9789b'
down_revision: Union[str, None] = 'e40bcd6bed30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('load_generator_nodes',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('worker_identifier', sa.String(length=128), nullable=False),
        sa.Column('worker_name', sa.String(length=100), nullable=False),
        sa.Column('hostname', sa.String(length=128), nullable=False),
        sa.Column('platform', sa.String(length=64), nullable=False),
        sa.Column('cpu_cores', sa.Integer(), nullable=False),
        sa.Column('total_memory_bytes', sa.BigInteger(), nullable=False),
        sa.Column('available_memory_bytes', sa.BigInteger(), nullable=False),
        sa.Column('locust_version', sa.String(length=32), nullable=False),
        sa.Column('software_version', sa.String(length=32), nullable=False),
        sa.Column('build_identifier', sa.String(length=64), nullable=False),
        sa.Column('auth_token_hash', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('registered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_load_generator_nodes_status'), 'load_generator_nodes', ['status'], unique=False)
    op.create_index(op.f('ix_load_generator_nodes_worker_identifier'), 'load_generator_nodes', ['worker_identifier'], unique=True)

    op.add_column('simulation_runs', sa.Column('execution_mode', sa.String(length=32), nullable=False, server_default='local'))
    op.add_column('simulation_workers', sa.Column('worker_node_id', sa.String(length=64), nullable=True))
    op.add_column('simulation_workers', sa.Column('assigned_users', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('simulation_workers', sa.Column('active_users', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('simulation_workers', sa.Column('worker_process_count', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('simulation_workers', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('simulation_workers', sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('simulation_workers', sa.Column('error_message', sa.Text(), nullable=True))
    op.create_index(op.f('ix_simulation_workers_status'), 'simulation_workers', ['status'], unique=False)
    op.create_index(op.f('ix_simulation_workers_worker_node_id'), 'simulation_workers', ['worker_node_id'], unique=False)
    op.create_foreign_key('fk_simulation_workers_worker_node_id', 'simulation_workers', 'load_generator_nodes', ['worker_node_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_simulation_workers_worker_node_id', 'simulation_workers', type_='foreignkey')
    op.drop_index(op.f('ix_simulation_workers_worker_node_id'), table_name='simulation_workers')
    op.drop_index(op.f('ix_simulation_workers_status'), table_name='simulation_workers')
    op.drop_column('simulation_workers', 'error_message')
    op.drop_column('simulation_workers', 'finished_at')
    op.drop_column('simulation_workers', 'started_at')
    op.drop_column('simulation_workers', 'worker_process_count')
    op.drop_column('simulation_workers', 'active_users')
    op.drop_column('simulation_workers', 'assigned_users')
    op.drop_column('simulation_workers', 'worker_node_id')
    op.drop_column('simulation_runs', 'execution_mode')
    op.drop_index(op.f('ix_load_generator_nodes_worker_identifier'), table_name='load_generator_nodes')
    op.drop_index(op.f('ix_load_generator_nodes_status'), table_name='load_generator_nodes')
    op.drop_table('load_generator_nodes')
