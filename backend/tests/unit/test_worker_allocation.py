"""Unit Tests for Worker Workload Distribution and Capacity Allocation."""

import pytest
from app.models.worker_node import LoadGeneratorNode
from app.services.worker_assignment_service import worker_assignment_service


def make_mock_worker(worker_id: str, capacity: int) -> LoadGeneratorNode:
    return LoadGeneratorNode(
        id=worker_id,
        worker_identifier=f"ident-{worker_id}",
        worker_name=f"Worker {worker_id}",
        hostname="localhost",
        platform="Darwin",
        locust_version="2.47.0",
        auth_token_hash="hash",
        capacity=capacity,
        status="online",
    )


def test_user_distribution_sum_invariance():
    """Verify that sum of assigned users strictly equals total_users across different workloads."""
    workers = [
        make_mock_worker("w1", 100),
        make_mock_worker("w2", 200),
        make_mock_worker("w3", 300),
    ]

    for total in [1, 2, 3, 5, 7, 10, 50, 100, 333, 777, 1000, 5000]:
        results = worker_assignment_service.distribute_users(
            total_users=total,
            total_spawn_rate=10.0,
            workers=workers,
        )
        allocated_sum = sum(u for _, u, _ in results)
        assert allocated_sum == total, f"Expected {total}, got {allocated_sum}"


def test_capacity_proportional_allocation():
    """Verify that user distribution accurately reflects node capacity proportions."""
    w1 = make_mock_worker("w1", 100)
    w2 = make_mock_worker("w2", 300)

    results = worker_assignment_service.distribute_users(
        total_users=400,
        total_spawn_rate=20.0,
        workers=[w1, w2],
    )

    user_map = {worker.id: u for worker, u, _ in results}
    assert user_map["w1"] == 100
    assert user_map["w2"] == 300


def test_fewer_users_than_workers():
    """Verify handling when total requested users is less than active worker count."""
    workers = [make_mock_worker(f"w{i}", 100) for i in range(5)]
    results = worker_assignment_service.distribute_users(
        total_users=3,
        total_spawn_rate=5.0,
        workers=workers,
    )

    allocated_sum = sum(u for _, u, _ in results)
    assert allocated_sum == 3
    positive_allocations = [u for _, u, _ in results if u > 0]
    assert len(positive_allocations) == 3
    assert all(u == 1 for u in positive_allocations)


def test_spawn_rate_conservation():
    """Verify that distributed spawn rates sum to total requested spawn rate."""
    workers = [
        make_mock_worker("w1", 100),
        make_mock_worker("w2", 200),
    ]

    results = worker_assignment_service.distribute_users(
        total_users=150,
        total_spawn_rate=15.5,
        workers=workers,
    )

    rate_sum = round(sum(r for _, _, r in results), 2)
    assert rate_sum == 15.5


def test_empty_workers():
    """Verify distribution with zero workers returns empty list."""
    results = worker_assignment_service.distribute_users(
        total_users=100,
        total_spawn_rate=10.0,
        workers=[],
    )
    assert results == []
