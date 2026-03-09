"""AI-powered execution plan generator and optimizer."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from anthropic import Anthropic

from adobe_experience.agent.models import (
    ExecutionPlan,
    ExecutionStep,
    OptimizationSuggestion,
    PlanComparison,
    PlanMetrics,
    PlanStatus,
    RetryPolicy,
    RiskLevel,
    StepType,
)
from adobe_experience.core.config import get_ai_credentials


logger = logging.getLogger(__name__)


class PlannerEngine:
    """AI-powered execution planner for AEP workflows."""
    
    def __init__(self, ai_provider: str = "anthropic"):
        """Initialize planner engine.
        
        Args:
            ai_provider: AI provider to use (anthropic or openai)
        """
        self.ai_provider = ai_provider
        self.client = None
        
        # Initialize AI client
        credentials = get_ai_credentials()
        if ai_provider == "anthropic" and "anthropic_key" in credentials:
            self.client = Anthropic(api_key=credentials["anthropic_key"])
        
        if not self.client:
            logger.warning("No AI client initialized for planner")
    
    def generate_plan(
        self,
        intent: str,
        context: Optional[Dict[str, Any]] = None,
        file_path: Optional[str] = None,
        project_dir: Optional[str] = None
    ) -> ExecutionPlan:
        """Generate an execution plan from user intent.
        
        Args:
            intent: User's goal/intent in natural language
            context: Additional context information
            file_path: Optional file path to analyze (single-file mode)
            project_dir: Optional directory with multiple files (multi-file mode)
            
        Returns:
            ExecutionPlan with steps to achieve the intent
        """
        logger.info(f"Generating plan for intent: {intent}")
        
        # Multi-file project mode
        if project_dir:
            return self._generate_project_plan(project_dir, intent, context)
        
        # Single file mode (existing logic)
        # Analyze file if provided
        file_info = {}
        if file_path:
            file_info = self._analyze_file(file_path)
        
        # Build prompt for AI
        prompt = self._build_plan_generation_prompt(intent, context, file_info)
        
        # Get AI response
        plan_data = {}
        if self.client:
            try:
                plan_data = self._call_ai_for_plan(prompt)
            except Exception as e:
                logger.warning(f"AI plan generation failed, using fallback: {e}")
                plan_data = {}
        
        # Fallback to rule-based planning if AI failed or not available
        if not plan_data or "steps" not in plan_data:
            plan_data = self._fallback_plan_generation(intent, file_info)
        
        # Create ExecutionPlan object
        plan = self._create_plan_from_data(intent, plan_data)
        
        # Calculate metrics
        plan.metrics = self._calculate_plan_metrics(plan)
        
        # Assess risk
        plan.risk_level = self._assess_risk_level(plan)
        
        logger.info(f"Generated plan {plan.plan_id} with {len(plan.steps)} steps")
        return plan
    
    def optimize_plan(
        self,
        plan: ExecutionPlan,
        constraints: Optional[Dict[str, Any]] = None
    ) -> ExecutionPlan:
        """Optimize an execution plan.
        
        Args:
            plan: Plan to optimize
            constraints: Optimization constraints (e.g., max_duration, prefer_cost)
            
        Returns:
            Optimized ExecutionPlan
        """
        logger.info(f"Optimizing plan {plan.plan_id}")
        
        if not self.client:
            logger.warning("No AI client available for optimization")
            plan.status = PlanStatus.READY
            return plan
        
        # Get optimization suggestions from AI
        suggestions = self._get_optimization_suggestions(plan, constraints)
        
        # Apply automatic optimizations
        for suggestion in suggestions:
            if suggestion.auto_applicable:
                self._apply_optimization(plan, suggestion)
                plan.optimizations_applied.append(suggestion.suggestion_id)
        
        # Recalculate metrics
        plan.metrics = self._calculate_plan_metrics(plan)
        plan.risk_level = self._assess_risk_level(plan)
        plan.status = PlanStatus.READY
        
        logger.info(f"Applied {len(plan.optimizations_applied)} optimizations")
        return plan
    
    def compare_alternatives(
        self,
        intent: str,
        context: Optional[Dict[str, Any]] = None
    ) -> PlanComparison:
        """Generate and compare alternative plans.
        
        Args:
            intent: User's goal/intent
            context: Additional context
            
        Returns:
            PlanComparison with multiple alternatives
        """
        logger.info("Generating alternative plans for comparison")
        
        # Generate different approaches
        approaches = [
            {"name": "Batch Only", "prefer": "simplicity"},
            {"name": "Streaming", "prefer": "real_time"},
            {"name": "Hybrid", "prefer": "balanced"}
        ]
        
        plans = []
        for approach in approaches:
            approach_context = {**(context or {}), **approach}
            plan = self.generate_plan(intent, approach_context)
            plan.name = approach["name"]
            plans.append(plan)
        
        # Build comparison matrix
        comparison_matrix = {}
        for plan in plans:
            comparison_matrix[plan.name] = {
                "duration": plan.metrics.estimated_duration_seconds if plan.metrics else 0,
                "api_calls": plan.metrics.estimated_api_calls if plan.metrics else 0,
                "complexity": len(plan.steps),
                "risk": plan.risk_level.value
            }
        
        # Get AI recommendation
        recommendation, reasoning = self._get_recommendation(plans, comparison_matrix)
        
        comparison = PlanComparison(
            comparison_id=str(uuid4()),
            plans=plans,
            recommendation=recommendation,
            reasoning=reasoning,
            comparison_matrix=comparison_matrix
        )
        
        return comparison
    
    def explain_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Generate detailed explanation of plan steps.
        
        Args:
            plan: Plan to explain
            
        Returns:
            Dict with explanations for each step
        """
        explanations = {}
        
        for step in plan.steps:
            explanations[step.step_id] = {
                "step_number": step.step_number,
                "name": step.name,
                "description": step.description,
                "why_needed": self._explain_step_purpose(step, plan),
                "dependencies": step.dependencies,
                "estimated_duration": f"{step.estimated_duration}s",
                "can_fail": not step.skippable,
                "requires_approval": step.validation_required
            }
        
        return {
            "plan_id": plan.plan_id,
            "overall_goal": plan.intent,
            "total_steps": len(plan.steps),
            "estimated_total_time": f"{plan.metrics.estimated_duration_seconds}s" if plan.metrics else "unknown",
            "risk_assessment": plan.risk_level.value,
            "step_explanations": explanations
        }
    
    def _analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a file to gather context for planning."""
        from pathlib import Path
        
        path = Path(file_path)
        
        if not path.exists():
            return {"error": "File not found"}
        
        file_info = {
            "path": str(path),
            "name": path.name,
            "extension": path.suffix,
            "size_bytes": path.stat().st_size,
            "size_mb": round(path.stat().st_size / (1024 * 1024), 2)
        }
        
        # For CSV/JSON files, analyze structure
        if path.suffix.lower() in ['.csv', '.json']:
            try:
                if path.suffix.lower() == '.csv':
                    import csv
                    with open(path, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)[:10]  # Sample first 10 rows
                        file_info["columns"] = list(rows[0].keys()) if rows else []
                        file_info["row_count_sample"] = len(rows)
                        file_info["sample_data"] = rows[:3]
                elif path.suffix.lower() == '.json':
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            file_info["record_count_sample"] = len(data[:10])
                            file_info["sample_data"] = data[:3]
                            if data:
                                file_info["fields"] = list(data[0].keys())
                        elif isinstance(data, dict):
                            file_info["fields"] = list(data.keys())
                            file_info["sample_data"] = {k: data[k] for k in list(data.keys())[:5]}
            except Exception as e:
                logger.warning(f"Could not analyze file structure: {e}")
                file_info["analysis_error"] = str(e)
        
        return file_info
    
    def _build_plan_generation_prompt(
        self,
        intent: str,
        context: Optional[Dict[str, Any]],
        file_info: Dict[str, Any]
    ) -> str:
        """Build prompt for AI plan generation."""
        prompt = f"""Generate an execution plan for the following AEP workflow task:

User Intent: {intent}

"""
        
        if file_info:
            prompt += f"""File Information:
- Name: {file_info.get('name', 'N/A')}
- Size: {file_info.get('size_mb', 0)} MB
- Type: {file_info.get('extension', 'unknown')}
"""
            if 'columns' in file_info:
                prompt += f"- Columns: {', '.join(file_info['columns'][:10])}\n"
            if 'row_count_sample' in file_info:
                prompt += f"- Estimated rows: ~{file_info['row_count_sample'] * 100}\n"
        
        if context:
            prompt += f"\nAdditional Context:\n{json.dumps(context, indent=2)}\n"
        
        prompt += """
Generate a step-by-step execution plan with:
1. Step name and description
2. Action type (validate_file, generate_schema, upload_file, etc.)
3. Parameters needed
4. Dependencies on previous steps
5. Estimated duration for each step
6. Whether step requires user validation

Return the plan as a JSON object with this structure:
{
  "name": "Plan name",
  "description": "What this plan accomplishes",
  "steps": [
    {
      "step_number": 1,
      "step_type": "validate_file",
      "name": "Validate CSV file",
      "description": "Check file format and structure",
      "action": "validate_csv",
      "parameters": {"file": "path/to/file.csv"},
      "dependencies": [],
      "estimated_duration": 5,
      "validation_required": false
    }
  ]
}
"""
        
        return prompt
    
    def _call_ai_for_plan(self, prompt: str) -> Dict[str, Any]:
        """Call AI to generate plan data."""
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Extract JSON from response
            content = response.content[0].text
            
            # Try to parse JSON from response
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()
            
            return json.loads(json_str)
            
        except Exception as e:
            logger.error(f"AI plan generation failed: {e}")
            return {}
    
    def _fallback_plan_generation(
        self,
        intent: str,
        file_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback plan generation without AI."""
        
        is_csv = file_info.get('extension', '').lower() == '.csv'
        
        steps_data = [
            {
                "step_number": 1,
                "step_type": "validate_file",
                "name": "Validate file",
                "description": f"Validate {file_info.get('name', 'file')} format and structure",
                "action": "validate_file",
                "parameters": {"file": file_info.get('path', '')},
                "dependencies": [],
                "estimated_duration": 5,
                "validation_required": False
            },
            {
                "step_number": 2,
                "step_type": "generate_schema",
                "name": "Generate XDM schema",
                "description": "Analyze data and generate XDM-compliant schema",
                "action": "generate_schema",
                "parameters": {"file": file_info.get('path', ''), "class": "profile"},
                "dependencies": ["step_1"],
                "estimated_duration": 10,
                "validation_required": True
            },
            {
                "step_number": 3,
                "step_type": "upload_schema",
                "name": "Upload schema to registry",
                "description": "Register schema in AEP Schema Registry",
                "action": "upload_schema",
                "parameters": {},
                "dependencies": ["step_2"],
                "estimated_duration": 3,
                "validation_required": False
            },
            {
                "step_number": 4,
                "step_type": "create_dataset",
                "name": "Create dataset",
                "description": "Create dataset with Profile enabled",
                "action": "create_dataset",
                "parameters": {"enable_profile": True},
                "dependencies": ["step_3"],
                "estimated_duration": 5,
                "validation_required": False
            },
            {
                "step_number": 5,
                "step_type": "create_batch",
                "name": "Create batch",
                "description": "Initialize batch for data ingestion",
                "action": "create_batch",
                "parameters": {},
                "dependencies": ["step_4"],
                "estimated_duration": 2,
                "validation_required": False
            },
            {
                "step_number": 6,
                "step_type": "upload_file",
                "name": "Upload data",
                "description": f"Upload {file_info.get('name', 'file')} to AEP",
                "action": "upload_file",
                "parameters": {"file": file_info.get('path', '')},
                "dependencies": ["step_5"],
                "estimated_duration": 15,
                "validation_required": False
            },
            {
                "step_number": 7,
                "step_type": "complete_batch",
                "name": "Complete batch",
                "description": "Finalize batch and trigger processing",
                "action": "complete_batch",
                "parameters": {},
                "dependencies": ["step_6"],
                "estimated_duration": 2,
                "validation_required": False
            },
            {
                "step_number": 8,
                "step_type": "validate_ingestion",
                "name": "Validate ingestion",
                "description": "Poll batch status and verify successful ingestion",
                "action": "validate_ingestion",
                "parameters": {"poll_interval": 5, "timeout": 300},
                "dependencies": ["step_7"],
                "estimated_duration": 30,
                "validation_required": False
            }
        ]
        
        return {
            "name": f"Ingest {file_info.get('name', 'data')} to AEP",
            "description": f"Complete workflow to ingest {file_info.get('name', 'file')} into Adobe Experience Platform",
            "steps": steps_data
        }
    
    def _create_plan_from_data(
        self,
        intent: str,
        plan_data: Dict[str, Any]
    ) -> ExecutionPlan:
        """Create ExecutionPlan object from plan data."""
        
        steps = []
        for step_data in plan_data.get('steps', []):
            step = ExecutionStep(
                step_id=f"step_{step_data['step_number']}",
                step_number=step_data['step_number'],
                step_type=StepType(step_data.get('step_type', 'validate_file')),
                name=step_data['name'],
                description=step_data['description'],
                action=step_data['action'],
                parameters=step_data.get('parameters', {}),
                dependencies=step_data.get('dependencies', []),
                estimated_duration=step_data.get('estimated_duration', 0),
                validation_required=step_data.get('validation_required', False),
                retry_policy=RetryPolicy()
            )
            steps.append(step)
        
        plan = ExecutionPlan(
            plan_id=str(uuid4()),
            version=1,
            name=plan_data.get('name', 'Unnamed Plan'),
            description=plan_data.get('description', ''),
            intent=intent,
            steps=steps,
            status=PlanStatus.DRAFT
        )
        
        return plan
    
    def _calculate_plan_metrics(self, plan: ExecutionPlan) -> PlanMetrics:
        """Calculate metrics for a plan."""
        
        total_duration = sum(s.estimated_duration for s in plan.steps)
        
        # Count API calls (rough estimate)
        api_call_types = ['upload_schema', 'create_dataset', 'create_batch', 'upload_file', 'complete_batch']
        api_calls = sum(1 for s in plan.steps if s.step_type.value in api_call_types)
        
        # Identify parallelizable steps
        parallelizable = 0
        for step in plan.steps:
            if len(step.dependencies) <= 1:  # Could potentially be parallelized
                parallelizable += 1
        
        return PlanMetrics(
            total_steps=len(plan.steps),
            estimated_duration_seconds=total_duration,
            estimated_api_calls=api_calls,
            parallelizable_steps=parallelizable,
            critical_path_duration=total_duration  # Simplified for now
        )
    
    def _assess_risk_level(self, plan: ExecutionPlan) -> RiskLevel:
        """Assess risk level of a plan."""
        
        risk_score = 0
        
        # More steps = higher risk
        if len(plan.steps) > 10:
            risk_score += 2
        elif len(plan.steps) > 5:
            risk_score += 1
        
        # Long duration = higher risk
        if plan.metrics and plan.metrics.estimated_duration_seconds > 300:
            risk_score += 2
        elif plan.metrics and plan.metrics.estimated_duration_seconds > 120:
            risk_score += 1
        
        # Many API calls = higher risk
        if plan.metrics and plan.metrics.estimated_api_calls > 10:
            risk_score += 1
        
        # Map score to risk level
        if risk_score == 0:
            return RiskLevel.VERY_LOW
        elif risk_score <= 2:
            return RiskLevel.LOW
        elif risk_score <= 4:
            return RiskLevel.MEDIUM
        elif risk_score <= 6:
            return RiskLevel.HIGH
        else:
            return RiskLevel.VERY_HIGH
    
    def _get_optimization_suggestions(
        self,
        plan: ExecutionPlan,
        constraints: Optional[Dict[str, Any]]
    ) -> List[OptimizationSuggestion]:
        """Get AI-powered optimization suggestions."""
        
        suggestions = []
        
        # Example: Suggest parallel execution
        if plan.metrics and plan.metrics.parallelizable_steps > 2:
            suggestions.append(OptimizationSuggestion(
                suggestion_id="opt_parallel",
                category="performance",
                title="Parallelize independent steps",
                description=f"Execute {plan.metrics.parallelizable_steps} independent steps in parallel",
                impact=f"Reduce execution time by ~{int((plan.metrics.parallelizable_steps - 1) * 5)}s",
                effort="low",
                auto_applicable=True
            ))
        
        # Example: Suggest batch size optimization
        upload_steps = [s for s in plan.steps if s.step_type == StepType.UPLOAD_FILE]
        if upload_steps:
            suggestions.append(OptimizationSuggestion(
                suggestion_id="opt_batch_size",
                category="performance",
                title="Optimize batch size",
                description="Adjust batch size based on file size for optimal throughput",
                impact="Improve upload speed by 20-30%",
                effort="low",
                auto_applicable=True
            ))
        
        return suggestions
    
    def _apply_optimization(
        self,
        plan: ExecutionPlan,
        suggestion: OptimizationSuggestion
    ) -> None:
        """Apply an optimization suggestion to a plan."""
        
        if suggestion.suggestion_id == "opt_parallel":
            # Mark independent steps as parallelizable
            for step in plan.steps:
                if len(step.dependencies) == 0:
                    step.parameters["parallel"] = True
        
        elif suggestion.suggestion_id == "opt_batch_size":
            # Adjust batch size
            for step in plan.steps:
                if step.step_type == StepType.UPLOAD_FILE:
                    step.parameters["batch_size"] = 1000
    
    def _get_recommendation(
        self,
        plans: List[ExecutionPlan],
        comparison_matrix: Dict[str, Dict[str, Any]]
    ) -> tuple[str, str]:
        """Get AI recommendation for best plan."""
        
        # Simple heuristic recommendation
        best_plan = min(plans, key=lambda p: p.metrics.estimated_duration_seconds if p.metrics else 999)
        
        recommendation = best_plan.name
        reasoning = (
            f"{best_plan.name} is recommended because it offers the fastest execution time "
            f"({best_plan.metrics.estimated_duration_seconds}s) with {best_plan.risk_level.value} risk."
        )
        
        return recommendation, reasoning
    
    def _explain_step_purpose(self, step: ExecutionStep, plan: ExecutionPlan) -> str:
        """Explain why a step is needed."""
        
        explanations = {
            StepType.VALIDATE_FILE: "Ensures the file is valid and readable before processing",
            StepType.GENERATE_SCHEMA: "Creates XDM schema definition matching your data structure",
            StepType.UPLOAD_SCHEMA: "Registers the schema in AEP for data validation",
            StepType.CREATE_DATASET: "Creates a container for your data in AEP",
            StepType.CREATE_BATCH: "Prepares a batch upload session",
            StepType.UPLOAD_FILE: "Transfers your data to AEP storage",
            StepType.COMPLETE_BATCH: "Finalizes the upload and triggers processing",
            StepType.VALIDATE_INGESTION: "Confirms data was successfully ingested"
        }
        
        return explanations.get(step.step_type, "Required workflow step")
    
    # ========================================================================
    # Multi-File Project Planning (Phase 2B)
    # ========================================================================
    
    def _generate_project_plan(
        self,
        project_dir: str,
        intent: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionPlan:
        """Generate comprehensive plan for multi-file project.
        
        Args:
            project_dir: Directory containing multiple data files
            intent: User's goal/intent
            context: Additional context
            
        Returns:
            ExecutionPlan with steps for all entities
        """
        from pathlib import Path
        from adobe_experience.schema.dataset_scanner import DatasetScanner
        from adobe_experience.agent.inference import AIInferenceEngine
        from adobe_experience.core.config import get_config
        import asyncio
        
        logger.info(f"Generating project plan for: {project_dir}")
        
        # Step 1: Scan directory for entities
        scanner = DatasetScanner(sample_size=10)
        scan_result = scanner.scan_directory(Path(project_dir))
        
        logger.info(f"Found {len(scan_result.entities)} entities in project")
        
        # Step 2: AI analysis for relationships and XDM recommendations
        config = get_config()
        ai_engine = AIInferenceEngine(config)
        
        try:
            analysis = asyncio.run(ai_engine.analyze_dataset_relationships(scan_result))
        except Exception as e:
            logger.error(f"ERD analysis failed: {e}")
            # Fallback: treat as independent entities
            analysis = None
        
        inferred_relationships = self._infer_relationship_candidates(
            [e.entity_name for e in scan_result.entities]
        )

        # Step 3: Calculate ingestion order based on relationships
        if analysis and analysis.relationships:
            entity_order = self._calculate_ingestion_order(
                [e.entity_name for e in scan_result.entities],
                analysis.relationships,
                analysis.xdm_class_recommendations
            )
            relationships_for_dependencies = analysis.relationships
        else:
            # No AI analysis available: use deterministic heuristic ordering.
            entity_order = self._fallback_entity_order(
                [e.entity_name for e in scan_result.entities]
            )
            relationships_for_dependencies = inferred_relationships
        
        logger.info(f"Ingestion order: {' → '.join(entity_order)}")
        
        # Step 4: Generate steps for each entity
        all_steps = []
        step_counter = 1
        entity_step_map = {}  # Track which steps belong to which entity
        
        for entity_name in entity_order:
            # Find entity metadata
            entity_meta = next((e for e in scan_result.entities if e.entity_name == entity_name), None)
            if not entity_meta:
                continue
            
            # Get XDM recommendation for this entity
            xdm_rec = None
            if analysis and analysis.xdm_class_recommendations:
                xdm_rec = next((r for r in analysis.xdm_class_recommendations if r.entity_name == entity_name), None)
            
            # Get identity strategy
            identity_strategy = None
            if analysis and analysis.identity_strategies:
                identity_strategy = next((s for s in analysis.identity_strategies if s.entity_name == entity_name), None)
            
            # Generate steps for this entity
            entity_steps = self._generate_entity_steps(
                entity_name=entity_name,
                entity_meta=entity_meta,
                xdm_recommendation=xdm_rec,
                identity_strategy=identity_strategy,
                step_number_start=step_counter,
                analysis=analysis
            )
            
            # Track steps for this entity
            entity_step_map[entity_name] = [s.step_id for s in entity_steps]
            
            all_steps.extend(entity_steps)
            step_counter += len(entity_steps)
        
        # Step 5: Add cross-entity dependencies
        if relationships_for_dependencies:
            self._add_cross_entity_dependencies(
                all_steps,
                entity_step_map,
                relationships_for_dependencies
            )
        
        # Step 6: Add final validation steps
        validation_step = ExecutionStep(
            step_id=f"step_{step_counter}",
            step_number=step_counter,
            step_type=StepType.VALIDATE_INGESTION,
            name="Validate Identity Graph",
            description="Verify all entity relationships and identity stitching",
            action="validate_identity_graph",
            parameters={
                "entities": entity_order,
                "check_relationships": True
            },
            dependencies=[s.step_id for s in all_steps[-len(entity_order):]],  # Depend on last steps of all entities
            estimated_duration=10,
            validation_required=False
        )
        all_steps.append(validation_step)
        step_counter += 1
        
        # Create plan
        plan = ExecutionPlan(
            plan_id=str(uuid4()),
            name=f"Multi-Entity Ingestion: {Path(project_dir).name}",
            description=f"Comprehensive ingestion plan for {len(scan_result.entities)} entities with relationship mapping",
            intent=intent,
            steps=all_steps,
            status=PlanStatus.DRAFT
        )
        
        # Add metadata about the project
        plan.parameters = {
            "project_dir": project_dir,
            "entity_count": len(scan_result.entities),
            "total_records": scan_result.total_records,
            "ingestion_order": entity_order,
            "has_relationships": bool(relationships_for_dependencies)
        }
        
        # Calculate metrics
        plan.metrics = self._calculate_plan_metrics(plan)
        plan.risk_level = self._assess_risk_level(plan)
        
        logger.info(f"Generated project plan with {len(all_steps)} steps")
        return plan
    
    def _calculate_ingestion_order(
        self,
        entities: List[str],
        relationships: List,
        xdm_recommendations: List
    ) -> List[str]:
        """Calculate optimal ingestion order using topological sort.
        
        Rules:
        1. Profile entities first (master data)
        2. Lookup entities second (reference data)
        3. Event entities last (fact data with FKs)
        4. Respect FK dependencies (parent before child)
        
        Args:
            entities: List of entity names
            relationships: List of EntityRelationship objects
            xdm_recommendations: List of XDM class recommendations
            
        Returns:
            Ordered list of entity names
        """
        from collections import defaultdict, deque
        
        # Build dependency graph: entity -> [entities it depends on]
        dependencies = defaultdict(list)
        in_degree = defaultdict(int)
        
        # Initialize all entities with 0 in-degree
        for entity in entities:
            in_degree[entity] = 0
        
        # Build graph from relationships
        for rel in relationships:
            # N:1 relationship means source depends on target
            # e.g., orders (N) -> customers (1) means orders depends on customers
            if rel.relationship_type.value in ["N:1", "N:M"]:
                source = rel.source_entity
                target = rel.target_entity
                
                if target not in dependencies[source]:
                    dependencies[source].append(target)
                    in_degree[source] += 1
        
        # Categorize entities by XDM class
        profiles = []
        lookups = []
        events = []
        others = []
        
        for entity in entities:
            xdm_rec = next((r for r in xdm_recommendations if r.entity_name == entity), None)
            if xdm_rec:
                if "Profile" in xdm_rec.recommended_class:
                    profiles.append(entity)
                elif "ExperienceEvent" in xdm_rec.recommended_class or "Event" in xdm_rec.recommended_class:
                    events.append(entity)
                elif "Product" in xdm_rec.recommended_class or "Lookup" in xdm_rec.recommended_class:
                    lookups.append(entity)
                else:
                    others.append(entity)
            else:
                others.append(entity)
        
        # Topological sort within each category
        def toposort(entity_list):
            queue = deque([e for e in entity_list if in_degree[e] == 0])
            result = []
            
            while queue:
                entity = queue.popleft()
                result.append(entity)
                
                # Process dependents
                for dependent in entities:
                    if entity in dependencies[dependent]:
                        in_degree[dependent] -= 1
                        if in_degree[dependent] == 0 and dependent in entity_list:
                            queue.append(dependent)
            
            # Add remaining entities (circular deps or not in queue)
            for entity in entity_list:
                if entity not in result:
                    result.append(entity)
            
            return result
        
        # Order: Profiles → Lookups → Others → Events
        ordered = []
        ordered.extend(toposort(profiles))
        ordered.extend(toposort(lookups))
        ordered.extend(toposort(others))
        ordered.extend(toposort(events))
        
        return ordered
    
    def _generate_entity_steps(
        self,
        entity_name: str,
        entity_meta,
        xdm_recommendation,
        identity_strategy,
        step_number_start: int,
        analysis
    ) -> List[ExecutionStep]:
        """Generate ingestion steps for a single entity.
        
        Args:
            entity_name: Name of the entity
            entity_meta: EntityMetadata object
            xdm_recommendation: XDMClassRecommendation (or None)
            identity_strategy: IdentityStrategy (or None)
            step_number_start: Starting step number
            analysis: Full analysis result
            
        Returns:
            List of ExecutionStep objects for this entity
        """
        steps = []
        step_num = step_number_start
        
        # Determine XDM class
        xdm_class = "profile"
        enable_profile = False
        if xdm_recommendation:
            if "Profile" in xdm_recommendation.recommended_class:
                xdm_class = "profile"
                enable_profile = True
            elif "ExperienceEvent" in xdm_recommendation.recommended_class:
                xdm_class = "experience-event"
                enable_profile = True
            else:
                xdm_class = "custom"
        
        # Step 1: Validate file
        steps.append(ExecutionStep(
            step_id=f"step_{step_num}",
            step_number=step_num,
            step_type=StepType.VALIDATE_FILE,
            name=f"[{entity_name}] Validate data",
            description=f"Validate {entity_name}.json format and structure",
            action="validate_file",
            parameters={
                "file": entity_meta.file_path,
                "entity": entity_name,
                "record_count": entity_meta.record_count
            },
            dependencies=[],
            estimated_duration=5,
            validation_required=False
        ))
        step_num += 1
        
        # Step 2: Generate schema
        schema_params = {
            "file": entity_meta.file_path,
            "entity": entity_name,
            "class": xdm_class,
            "enable_profile": enable_profile
        }
        
        if identity_strategy:
            schema_params["primary_identity"] = identity_strategy.primary_identity_field
            schema_params["identity_namespace"] = identity_strategy.identity_namespace
        
        if xdm_recommendation and hasattr(analysis, 'field_group_suggestions'):
            fg_suggestions = analysis.field_group_suggestions.get(entity_name, [])
            if fg_suggestions:
                schema_params["field_groups"] = fg_suggestions
        
        steps.append(ExecutionStep(
            step_id=f"step_{step_num}",
            step_number=step_num,
            step_type=StepType.GENERATE_SCHEMA,
            name=f"[{entity_name}] Generate XDM schema",
            description=f"Create {xdm_class} schema for {entity_name}",
            action="generate_schema",
            parameters=schema_params,
            dependencies=[f"step_{step_num - 1}"],
            estimated_duration=10,
            validation_required=True,
            retry_policy=RetryPolicy(max_retries=2, retry_delay=5, backoff_multiplier=2.0)
        ))
        schema_step_id = f"step_{step_num}"
        step_num += 1
        
        # Step 3: Upload schema
        steps.append(ExecutionStep(
            step_id=f"step_{step_num}",
            step_number=step_num,
            step_type=StepType.UPLOAD_SCHEMA,
            name=f"[{entity_name}] Upload schema",
            description=f"Register {entity_name} schema in AEP",
            action="upload_schema",
            parameters={"entity": entity_name},
            dependencies=[schema_step_id],
            estimated_duration=3,
            validation_required=False
        ))
        upload_schema_step_id = f"step_{step_num}"
        step_num += 1
        
        # Step 4: Create dataset
        steps.append(ExecutionStep(
            step_id=f"step_{step_num}",
            step_number=step_num,
            step_type=StepType.CREATE_DATASET,
            name=f"[{entity_name}] Create dataset",
            description=f"Create dataset for {entity_name} (Profile: {enable_profile})",
            action="create_dataset",
            parameters={
                "entity": entity_name,
                "enable_profile": enable_profile,
                "enable_identity": bool(identity_strategy)
            },
            dependencies=[upload_schema_step_id],
            estimated_duration=5,
            validation_required=False
        ))
        dataset_step_id = f"step_{step_num}"
        step_num += 1
        
        # Step 5: Create batch
        steps.append(ExecutionStep(
            step_id=f"step_{step_num}",
            step_number=step_num,
            step_type=StepType.CREATE_BATCH,
            name=f"[{entity_name}] Create batch",
            description=f"Initialize batch upload for {entity_meta.record_count} records",
            action="create_batch",
            parameters={"entity": entity_name},
            dependencies=[dataset_step_id],
            estimated_duration=2,
            validation_required=False
        ))
        batch_step_id = f"step_{step_num}"
        step_num += 1
        
        # Step 6: Upload data
        upload_duration = max(10, entity_meta.record_count // 100)  # Estimate based on record count
        steps.append(ExecutionStep(
            step_id=f"step_{step_num}",
            step_number=step_num,
            step_type=StepType.UPLOAD_FILE,
            name=f"[{entity_name}] Ingest data",
            description=f"Upload {entity_meta.record_count} records to AEP",
            action="upload_file",
            parameters={
                "file": entity_meta.file_path,
                "entity": entity_name,
                "record_count": entity_meta.record_count
            },
            dependencies=[batch_step_id],
            estimated_duration=upload_duration,
            validation_required=False,
            retry_policy=RetryPolicy(max_retries=3, retry_delay=10, backoff_multiplier=2.0)
        ))
        upload_step_id = f"step_{step_num}"
        step_num += 1
        
        # Step 7: Complete batch
        steps.append(ExecutionStep(
            step_id=f"step_{step_num}",
            step_number=step_num,
            step_type=StepType.COMPLETE_BATCH,
            name=f"[{entity_name}] Complete batch",
            description=f"Finalize {entity_name} batch and trigger processing",
            action="complete_batch",
            parameters={"entity": entity_name},
            dependencies=[upload_step_id],
            estimated_duration=2,
            validation_required=False
        ))
        complete_step_id = f"step_{step_num}"
        step_num += 1
        
        # Step 8: Validate ingestion
        steps.append(ExecutionStep(
            step_id=f"step_{step_num}",
            step_number=step_num,
            step_type=StepType.VALIDATE_INGESTION,
            name=f"[{entity_name}] Validate ingestion",
            description=f"Verify {entity_name} data ingested successfully",
            action="validate_ingestion",
            parameters={
                "entity": entity_name,
                "expected_records": entity_meta.record_count
            },
            dependencies=[complete_step_id],
            estimated_duration=15,
            validation_required=False
        ))
        
        return steps
    
    def _add_cross_entity_dependencies(
        self,
        all_steps: List[ExecutionStep],
        entity_step_map: Dict[str, List[str]],
        relationships: List
    ) -> None:
        """Add dependencies between entities based on relationships.
        
        Modifies all_steps in place by adding cross-entity dependencies.
        
        Args:
            all_steps: All generated steps
            entity_step_map: Map of entity_name -> list of step_ids
            relationships: List of EntityRelationship objects
        """
        # For each relationship, ensure dependent entity waits for parent entity's schema
        for rel in relationships:
            rel_type = None
            source_entity = None
            target_entity = None

            if isinstance(rel, dict):
                rel_type = rel.get("relationship_type")
                source_entity = rel.get("source_entity")
                target_entity = rel.get("target_entity")
            else:
                relationship_type = getattr(rel, "relationship_type", None)
                rel_type = getattr(relationship_type, "value", relationship_type)
                source_entity = getattr(rel, "source_entity", None)
                target_entity = getattr(rel, "target_entity", None)

            if rel_type in ["N:1", "N:M"]:
                # Source entity depends on target entity
                # e.g., orders depends on customers
                if source_entity not in entity_step_map or target_entity not in entity_step_map:
                    continue
                
                # Find the schema upload step of the target (parent) entity
                target_schema_step = None
                for step in all_steps:
                    if (step.step_type == StepType.UPLOAD_SCHEMA and 
                        step.parameters.get("entity") == target_entity):
                        target_schema_step = step.step_id
                        break
                
                if not target_schema_step:
                    continue
                
                # Add dependency to source entity's schema generation step
                for step in all_steps:
                    if (step.step_type == StepType.GENERATE_SCHEMA and 
                        step.parameters.get("entity") == source_entity):
                        if target_schema_step not in step.dependencies:
                            step.dependencies.append(target_schema_step)
                            logger.info(f"Added dependency: {source_entity} schema waits for {target_entity} schema")
                        break

    def _fallback_entity_order(self, entities: List[str]) -> List[str]:
        """Return deterministic ingestion order when AI analysis is unavailable."""
        profiles: List[str] = []
        lookups: List[str] = []
        events: List[str] = []
        others: List[str] = []

        for entity in entities:
            lowered = entity.lower()
            if any(token in lowered for token in ["customer", "profile", "account", "user"]):
                profiles.append(entity)
            elif any(token in lowered for token in ["product", "catalog", "category", "sku"]):
                lookups.append(entity)
            elif any(token in lowered for token in ["order", "event", "transaction", "click", "purchase"]):
                events.append(entity)
            else:
                others.append(entity)

        return sorted(profiles) + sorted(lookups) + sorted(others) + sorted(events)

    def _infer_relationship_candidates(self, entities: List[str]) -> List[Dict[str, str]]:
        """Infer minimal relationship candidates for dependency-safe ordering."""
        names = {name.lower(): name for name in entities}
        inferred: List[Dict[str, str]] = []

        if "orders" in names and "customers" in names:
            inferred.append(
                {
                    "source_entity": names["orders"],
                    "target_entity": names["customers"],
                    "relationship_type": "N:1",
                }
            )

        if "orders" in names and "products" in names:
            inferred.append(
                {
                    "source_entity": names["orders"],
                    "target_entity": names["products"],
                    "relationship_type": "N:M",
                }
            )

        return inferred
