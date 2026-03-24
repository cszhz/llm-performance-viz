#!/usr/bin/env python3
"""
Test script to verify project-based API endpoints.
"""

import sys
import json
sys.path.insert(0, '/home/ubuntu/mytest/llm-performance-viz/src')

from llm_test_tool.viz_server import ResultsDataProvider


def test_project_structure():
    """Test project detection and data loading"""
    print("=" * 60)
    print("Testing Project Structure")
    print("=" * 60)

    # Initialize provider
    provider = ResultsDataProvider("archive_results")

    # Test 1: Get available projects
    print("\n✓ Test 1: Get available projects")
    projects = provider.get_available_projects()
    print(f"  Available projects: {projects}")
    assert "default" in projects, "default project should exist"
    assert "project-a" in projects, "project-a should exist"
    print("  PASSED")

    # Test 2: Load default project
    print("\n✓ Test 2: Load default project")
    provider.load_all_results(project_name="default")
    print(f"  Loaded {len(provider.data)} records from default project")
    assert len(provider.data) > 0, "Should have data in default project"
    print("  PASSED")

    # Test 3: Load project-a
    print("\n✓ Test 3: Load project-a")
    provider.load_all_results(project_name="project-a")
    print(f"  Loaded {len(provider.data)} records from project-a")
    assert len(provider.data) > 0, "Should have data in project-a"
    print("  PASSED")

    # Test 4: Get combinations for current project
    print("\n✓ Test 4: Get combinations")
    combinations = provider.get_combinations()
    print(f"  Found {len(combinations)} combinations")
    assert len(combinations) > 0, "Should have combinations"
    print(f"  Sample: {combinations[0]}")
    print("  PASSED")

    # Test 5: Check data isolation
    print("\n✓ Test 5: Check data isolation between projects")
    provider.load_all_results(project_name="default")
    default_models = [c['model_name'] for c in provider.get_combinations()]

    provider.load_all_results(project_name="project-a")
    project_a_models = [c['model_name'] for c in provider.get_combinations()]

    print(f"  Default models: {default_models}")
    print(f"  Project-a models: {project_a_models}")
    assert default_models != project_a_models, "Projects should have different data"
    print("  PASSED")

    print("\n" + "=" * 60)
    print("All tests PASSED! ✓")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_project_structure()
    except Exception as e:
        print(f"\n✗ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
