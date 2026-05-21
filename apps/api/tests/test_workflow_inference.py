"""
Tests for Workflow Inference Engine
"""

import pytest
from datetime import datetime, timedelta
from app.services.workflow_inference import (
    WorkflowInferencer,
    ProcessMiner,
    DependencyMapper,
    BottleneckAnalyzer,
    SOPGenerator,
    WorkflowOptimizer,
    WorkflowNode,
    WorkflowEdge,
    WorkflowGraph,
)


@pytest.fixture
def sample_events():
    """Sample ticket/task events for testing."""
    base_time = datetime.utcnow()
    return [
        {
            "id": "event-1",
            "timestamp": base_time,
            "action": "ticket_created",
            "description": "Customer refund request",
            "duration_minutes": 0,
            "success": True,
        },
        {
            "id": "event-2",
            "timestamp": base_time + timedelta(minutes=5),
            "action": "validate_customer",
            "description": "Validate customer status",
            "duration_minutes": 5,
            "success": True,
        },
        {
            "id": "event-3",
            "timestamp": base_time + timedelta(minutes=15),
            "action": "check_approval",
            "description": "Check if approval needed",
            "duration_minutes": 2,
            "success": True,
        },
        {
            "id": "event-4",
            "timestamp": base_time + timedelta(minutes=20),
            "action": "request_approval",
            "description": "Request manager approval",
            "duration_minutes": 30,
            "success": True,
        },
        {
            "id": "event-5",
            "timestamp": base_time + timedelta(minutes=60),
            "action": "process_refund",
            "description": "Process refund payment",
            "duration_minutes": 15,
            "success": True,
        },
        {
            "id": "event-6",
            "timestamp": base_time + timedelta(minutes=80),
            "action": "send_confirmation",
            "description": "Send confirmation email",
            "duration_minutes": 1,
            "success": True,
        },
        {
            "id": "event-7",
            "timestamp": base_time + timedelta(minutes=85),
            "action": "close_ticket",
            "description": "Close ticket",
            "duration_minutes": 0,
            "success": True,
        },
    ]


@pytest.fixture
def sample_conversation_history():
    """Sample conversation history with workflow steps."""
    return [
        {
            "id": "msg-1",
            "content": "To process refunds: First receive request, then validate customer",
            "timestamp": datetime.utcnow(),
        },
        {
            "id": "msg-2",
            "content": "After validation, check if amount requires approval",
            "timestamp": datetime.utcnow(),
        },
        {
            "id": "msg-3",
            "content": "If > $1000, request manager approval",
            "timestamp": datetime.utcnow(),
        },
        {
            "id": "msg-4",
            "content": "Once approved, process refund and send confirmation",
            "timestamp": datetime.utcnow(),
        },
    ]


@pytest.fixture
def sample_workflow_nodes():
    """Sample workflow nodes."""
    return [
        WorkflowNode(
            id="start",
            name="Receive Request",
            action_type="task",
            description="Receive refund request",
            duration_minutes=0,
        ),
        WorkflowNode(
            id="validate",
            name="Validate Customer",
            action_type="task",
            description="Validate customer status",
            duration_minutes=5,
            dependencies=["start"],
        ),
        WorkflowNode(
            id="check_amount",
            name="Check Amount",
            action_type="decision",
            description="Check if approval needed",
            duration_minutes=2,
            dependencies=["validate"],
        ),
        WorkflowNode(
            id="request_approval",
            name="Request Approval",
            action_type="approval",
            description="Request manager approval",
            duration_minutes=30,
            dependencies=["check_amount"],
        ),
        WorkflowNode(
            id="process",
            name="Process Refund",
            action_type="task",
            description="Process refund payment",
            duration_minutes=15,
            dependencies=["request_approval"],
        ),
        WorkflowNode(
            id="notify",
            name="Send Notification",
            action_type="task",
            description="Send confirmation email",
            duration_minutes=1,
            dependencies=["process"],
        ),
        WorkflowNode(
            id="end",
            name="Close",
            action_type="end",
            description="Close ticket",
            duration_minutes=0,
            dependencies=["notify"],
        ),
    ]


@pytest.fixture
def sample_workflow_graph(sample_workflow_nodes):
    """Sample workflow graph."""
    edges = [
        WorkflowEdge(source="start", target="validate", frequency=10, success_rate=0.95),
        WorkflowEdge(source="validate", target="check_amount", frequency=10, success_rate=0.98),
        WorkflowEdge(
            source="check_amount",
            target="request_approval",
            label="amount > $1000",
            frequency=6,
            success_rate=0.92,
        ),
        WorkflowEdge(
            source="check_amount",
            target="process",
            label="amount <= $1000",
            frequency=4,
            success_rate=0.99,
        ),
        WorkflowEdge(source="request_approval", target="process", frequency=6, success_rate=0.90),
        WorkflowEdge(source="process", target="notify", frequency=10, success_rate=0.97),
        WorkflowEdge(source="notify", target="end", frequency=10, success_rate=0.99),
    ]

    return WorkflowGraph(
        id="workflow-refund",
        name="Refund Processing",
        description="End-to-end refund processing workflow",
        nodes=sample_workflow_nodes,
        edges=edges,
        start_node="start",
        end_nodes=["end"],
        average_duration_minutes=53,
        success_rate=0.94,
        total_executions=10,
    )


class TestProcessMiner:
    @pytest.mark.asyncio
    async def test_mine_processes(self, sample_events):
        """Test process mining from events."""
        miner = ProcessMiner()

        processes = await miner.mine_processes(sample_events)

        assert isinstance(processes, list)
        assert len(processes) > 0
        for process in processes:
            assert "sequence" in process
            assert "frequency" in process
            assert "success_rate" in process

    @pytest.mark.asyncio
    async def test_extract_event_sequences(self, sample_events):
        """Test event sequence extraction."""
        miner = ProcessMiner()

        sequences = miner._extract_event_sequences(sample_events)

        assert isinstance(sequences, list)
        assert len(sequences) > 0
        for seq in sequences:
            assert isinstance(seq, list)
            assert all(isinstance(e, str) for e in seq)


class TestDependencyMapper:
    @pytest.mark.asyncio
    async def test_map_dependencies(self, sample_workflow_nodes):
        """Test dependency mapping."""
        mapper = DependencyMapper()

        deps = await mapper.map_dependencies(sample_workflow_nodes)

        assert isinstance(deps, dict)
        # Start should have no dependencies
        assert deps["start"] == []
        # Validate should depend on start
        assert "start" in deps["validate"]

    @pytest.mark.asyncio
    async def test_find_critical_path(self, sample_workflow_graph):
        """Test critical path identification."""
        mapper = DependencyMapper()

        paths = mapper.find_critical_path(sample_workflow_graph)

        assert isinstance(paths, list)
        assert len(paths) > 0
        for path in paths:
            assert isinstance(path, list)
            assert len(path) > 0


class TestBottleneckAnalyzer:
    @pytest.mark.asyncio
    async def test_analyze_bottlenecks(self, sample_workflow_graph):
        """Test bottleneck analysis."""
        analyzer = BottleneckAnalyzer()

        bottlenecks = await analyzer.analyze_bottlenecks(sample_workflow_graph)

        assert isinstance(bottlenecks, list)
        # Should identify some bottlenecks (high duration or low success rate)
        if bottlenecks:
            for bn in bottlenecks:
                assert "node_id" in bn
                assert "severity" in bn
                assert "reason" in bn

    @pytest.mark.asyncio
    async def test_find_sequential_chains(self, sample_workflow_graph):
        """Test sequential chain identification."""
        analyzer = BottleneckAnalyzer()

        chains = analyzer._find_sequential_chains(sample_workflow_graph)

        assert isinstance(chains, list)
        # Should have at least one chain
        for chain in chains:
            assert isinstance(chain, list)
            assert len(chain) >= 2


class TestSOPGenerator:
    def test_generate_sop(self, sample_workflow_graph):
        """Test SOP generation."""
        generator = SOPGenerator()

        sop = generator.generate_sop(sample_workflow_graph, format="json")

        assert isinstance(sop, dict)
        assert "title" in sop
        assert "steps" in sop
        assert isinstance(sop["steps"], list)

    def test_generate_sop_markdown(self, sample_workflow_graph):
        """Test markdown SOP generation."""
        generator = SOPGenerator()

        sop = generator.generate_sop(sample_workflow_graph, format="markdown")

        assert isinstance(sop, str)
        assert "#" in sop  # Markdown heading
        assert "Step" in sop or "step" in sop

    def test_generate_markdown_sop(self, sample_workflow_graph):
        """Test markdown SOP formatting."""
        generator = SOPGenerator()

        sop_text = generator._generate_markdown_sop(sample_workflow_graph)

        assert isinstance(sop_text, str)
        assert len(sop_text) > 0
        assert "Refund Processing" in sop_text or "refund" in sop_text.lower()


class TestWorkflowOptimizer:
    @pytest.mark.asyncio
    async def test_optimize_workflow(self, sample_workflow_graph):
        """Test workflow optimization."""
        optimizer = WorkflowOptimizer()

        optimized = await optimizer.optimize_workflow(sample_workflow_graph)

        assert isinstance(optimized, dict)
        assert "optimizations" in optimized
        assert isinstance(optimized["optimizations"], list)

    @pytest.mark.asyncio
    async def test_find_parallelization(self, sample_workflow_graph):
        """Test parallelization opportunities."""
        optimizer = WorkflowOptimizer()

        opps = optimizer._find_parallelization(sample_workflow_graph)

        assert isinstance(opps, list)
        for opp in opps:
            assert "nodes" in opp
            assert "potential_savings_minutes" in opp

    @pytest.mark.asyncio
    async def test_find_automation_opportunities(self, sample_workflow_graph):
        """Test automation opportunity detection."""
        optimizer = WorkflowOptimizer()

        opps = optimizer._find_automation_opps(sample_workflow_graph)

        assert isinstance(opps, list)
        for opp in opps:
            assert "node_id" in opp
            assert "automation_potential" in opp


class TestWorkflowInferencer:
    @pytest.mark.asyncio
    async def test_infer_workflows(self, sample_events, sample_conversation_history):
        """Test full workflow inference."""
        inferencer = WorkflowInferencer()

        workflows = await inferencer.infer_workflows(
            events=sample_events,
            conversation_history=sample_conversation_history,
            category="operations",
        )

        assert isinstance(workflows, list)
        if workflows:
            workflow = workflows[0]
            assert hasattr(workflow, "id")
            assert hasattr(workflow, "name")
            assert hasattr(workflow, "nodes")
            assert hasattr(workflow, "edges")
            assert workflow.start_node is not None
            assert len(workflow.end_nodes) > 0

    @pytest.mark.asyncio
    async def test_infer_workflows_with_documents(self, sample_conversation_history):
        """Test workflow inference from documents."""
        inferencer = WorkflowInferencer()

        # Convert conversation to document format
        documents = [
            {
                "id": f"doc-{i}",
                "content": msg["content"],
                "created_at": msg["timestamp"].isoformat(),
            }
            for i, msg in enumerate(sample_conversation_history)
        ]

        workflows = await inferencer.infer_workflows(
            documents=documents,
            category="operations",
        )

        assert isinstance(workflows, list)


class TestWorkflowGraph:
    def test_workflow_graph_to_dict(self, sample_workflow_graph):
        """Test workflow graph serialization."""
        result = sample_workflow_graph.to_dict()

        assert isinstance(result, dict)
        assert "id" in result
        assert "name" in result
        assert "nodes" in result
        assert "edges" in result
        assert isinstance(result["nodes"], list)
        assert isinstance(result["edges"], list)


class TestWorkflowNode:
    def test_workflow_node_creation(self):
        """Test workflow node creation."""
        node = WorkflowNode(
            id="test-node",
            name="Test Task",
            action_type="task",
            description="Test description",
            duration_minutes=10,
        )

        assert node.id == "test-node"
        assert node.name == "Test Task"
        assert node.action_type == "task"
        assert node.duration_minutes == 10
        assert node.dependencies == []

    def test_workflow_node_with_dependencies(self):
        """Test workflow node with dependencies."""
        node = WorkflowNode(
            id="test-node",
            name="Test Task",
            action_type="task",
            dependencies=["dep-1", "dep-2"],
        )

        assert len(node.dependencies) == 2
        assert "dep-1" in node.dependencies


class TestWorkflowEdge:
    def test_workflow_edge_creation(self):
        """Test workflow edge creation."""
        edge = WorkflowEdge(
            source="node-1",
            target="node-2",
            label="success",
            frequency=10,
            success_rate=0.95,
        )

        assert edge.source == "node-1"
        assert edge.target == "node-2"
        assert edge.label == "success"
        assert edge.frequency == 10
        assert edge.success_rate == 0.95


@pytest.mark.asyncio
async def test_end_to_end_workflow_inference(sample_events, sample_conversation_history):
    """Test end-to-end workflow inference pipeline."""
    inferencer = WorkflowInferencer()

    workflows = await inferencer.infer_workflows(
        events=sample_events,
        conversation_history=sample_conversation_history,
        category="operations",
    )

    assert isinstance(workflows, list)
    assert len(workflows) > 0

    workflow = workflows[0]
    assert len(workflow.nodes) > 0
    assert len(workflow.edges) > 0
    assert workflow.average_duration_minutes >= 0
    assert 0 <= workflow.success_rate <= 1
    assert workflow.total_executions >= 0


@pytest.mark.asyncio
async def test_workflow_sop_generation(sample_workflow_graph):
    """Test SOP generation from workflow."""
    generator = SOPGenerator()

    sop_json = generator.generate_sop(sample_workflow_graph, format="json")
    sop_markdown = generator.generate_sop(sample_workflow_graph, format="markdown")

    assert isinstance(sop_json, dict)
    assert isinstance(sop_markdown, str)
    assert len(sop_markdown) > 0
