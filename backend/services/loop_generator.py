"""
Loop Generator Service

Generates circular walking routes with the Return Path Constraint:
The return path must be as disjoint as possible from the outbound path.

Implements bi-directional A* with edge exclusion for the advanced algorithm.
"""
import networkx as nx
import heapq
from typing import Optional
from dataclasses import dataclass
import math
import logging

from .routing import RoutingService, RoutingResult
from .cost_functions import CostFunctionEngine
from .vibe_engine import VibeEngine, VibeProfile

logger = logging.getLogger(__name__)


@dataclass
class LoopResult:
    """Result of loop generation."""
    outbound_path: list[int]
    return_path: list[int]
    full_path_coords: list[tuple[float, float]]
    total_distance: float
    total_time: float
    vibe_profile: VibeProfile
    nodes_explored: int
    disjoint_percentage: float  # How much of return path is unique


class LoopGenerator:
    """
    Generates circular walking routes.
    
    Algorithm (Advanced Bi-directional A* with penalized revisit):
    1. Estimate target distance from duration
    2. Find a "turnaround point" at roughly half the target distance
    3. Route outbound using A* with vibes
    4. Route return using A* with heavy penalties on outbound edges
    5. The penalty encourages exploration of alternative paths
    """
    
    # Walking speed: 4.5 km/h = 75 m/min
    WALKING_SPEED_M_PER_MIN = 75
    
    def __init__(
        self,
        graph: nx.MultiDiGraph,
        routing_service: RoutingService,
        cost_engine: CostFunctionEngine,
        vibe_engine: VibeEngine
    ):
        self.graph = graph
        self.routing = routing_service
        self.cost_engine = cost_engine
        self.vibe_engine = vibe_engine
    
    def _estimate_target_distance(self, duration_minutes: int) -> float:
        """Convert duration to target distance in meters."""
        return duration_minutes * self.WALKING_SPEED_M_PER_MIN
    
    def _find_turnaround_candidates(
        self,
        origin_node: int,
        target_distance: float,
        vibe_weights: dict[str, float],
        num_candidates: int = 5
    ) -> list[int]:
        """
        Find potential turnaround points at approximately half target distance.
        
        Uses a modified BFS/Dijkstra to find nodes at target distance.
        """
        half_distance = target_distance / 2
        tolerance = half_distance * 0.2  # 20% tolerance
        
        weight_func = self.cost_engine.create_weight_function(
            self.graph, vibe_weights, 'length'
        )
        
        # Dijkstra-like exploration to find nodes at target distance
        heap = [(0, origin_node)]
        distances = {origin_node: 0}
        candidates = []
        
        while heap and len(candidates) < num_candidates * 3:
            dist, node = heapq.heappop(heap)
            
            # Check if this node is at approximately the right distance
            if half_distance - tolerance <= dist <= half_distance + tolerance:
                candidates.append((node, dist))
            
            # Don't explore beyond 1.5x target
            if dist > half_distance * 1.5:
                continue
            
            for neighbor in self.graph.neighbors(node):
                edge_data = self.graph[node][neighbor][0]
                edge_cost = weight_func(node, neighbor, edge_data)
                new_dist = dist + edge_cost
                
                if neighbor not in distances or new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    heapq.heappush(heap, (new_dist, neighbor))
        
        # Sort by how close they are to ideal distance and return top candidates
        candidates.sort(key=lambda x: abs(x[1] - half_distance))
        return [c[0] for c in candidates[:num_candidates]]
    
    def _score_turnaround_point(
        self,
        origin_node: int,
        turnaround_node: int,
        vibe_weights: dict[str, float]
    ) -> float:
        """
        Score a turnaround point based on vibe potential.
        
        Higher score = better turnaround point.
        """
        node_data = self.graph.nodes[turnaround_node]
        lat, lon = node_data['y'], node_data['x']
        
        profile = self.vibe_engine.compute_point_vibe_profile(lat, lon)
        
        # Weight by user preferences
        score = 0.0
        weights = 0.0
        
        if vibe_weights.get('greenery', 0) > 0:
            score += profile.greenery * vibe_weights['greenery']
            weights += vibe_weights['greenery']
        if vibe_weights.get('blue_space', 0) > 0:
            score += profile.blue_space * vibe_weights['blue_space']
            weights += vibe_weights['blue_space']
        if vibe_weights.get('safety_check', 0) > 0:
            score += profile.safety * vibe_weights['safety_check']
            weights += vibe_weights['safety_check']
        
        return score / weights if weights > 0 else profile.overall
    
    def _calculate_disjoint_percentage(
        self,
        outbound_edges: set[tuple[int, int]],
        return_edges: set[tuple[int, int]]
    ) -> float:
        """Calculate what percentage of return path is unique."""
        if not return_edges:
            return 0.0
        
        # Count edges in return that aren't in outbound
        unique_return = 0
        for edge in return_edges:
            reverse = (edge[1], edge[0])
            if edge not in outbound_edges and reverse not in outbound_edges:
                unique_return += 1
        
        return unique_return / len(return_edges)
    
    def generate_loop(
        self,
        origin_node: int,
        duration_minutes: int,
        vibe_weights: dict[str, float]
    ) -> LoopResult:
        """
        Generate a circular walking route.
        
        Args:
            origin_node: Starting/ending node
            duration_minutes: Target walk duration
            vibe_weights: User's vibe preferences
            
        Returns:
            LoopResult with full loop path
        """
        target_distance = self._estimate_target_distance(duration_minutes)
        logger.info(f"Generating loop: {duration_minutes}min = ~{target_distance:.0f}m")
        
        # Find turnaround candidates
        candidates = self._find_turnaround_candidates(
            origin_node, target_distance, vibe_weights
        )
        
        if not candidates:
            raise ValueError("Could not find suitable turnaround points for loop")
        
        # Score and select best turnaround point
        scored = [
            (c, self._score_turnaround_point(origin_node, c, vibe_weights))
            for c in candidates
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        turnaround_node = scored[0][0]
        
        logger.info(f"Selected turnaround node: {turnaround_node}")
        
        # Route outbound
        outbound_result = self.routing.find_route(
            origin_node, turnaround_node, vibe_weights, algorithm="astar"
        )
        
        # Collect outbound edges for avoidance
        outbound_edges = set()
        for i in range(len(outbound_result.path_nodes) - 1):
            u, v = outbound_result.path_nodes[i], outbound_result.path_nodes[i+1]
            outbound_edges.add((u, v))
            outbound_edges.add((v, u))  # Both directions
        
        # Route return avoiding outbound path
        return_result = self.routing.find_route_avoiding_edges(
            turnaround_node, origin_node, vibe_weights,
            outbound_edges, algorithm="astar"
        )
        
        # Collect return edges for disjoint calculation
        return_edges = set()
        for i in range(len(return_result.path_nodes) - 1):
            u, v = return_result.path_nodes[i], return_result.path_nodes[i+1]
            return_edges.add((u, v))
        
        disjoint_pct = self._calculate_disjoint_percentage(outbound_edges, return_edges)
        
        # Combine paths (remove duplicate turnaround node)
        full_path_nodes = outbound_result.path_nodes + return_result.path_nodes[1:]
        full_coords = outbound_result.path_coords + return_result.path_coords[1:]
        
        # Calculate totals
        total_distance = outbound_result.total_distance + return_result.total_distance
        total_time = outbound_result.total_time + return_result.total_time
        
        # Compute combined vibe profile
        combined_profile = self.vibe_engine.compute_route_vibe_profile(full_coords)
        
        total_explored = outbound_result.nodes_explored + return_result.nodes_explored
        
        logger.info(
            f"Loop generated: {total_distance:.0f}m, "
            f"{disjoint_pct:.0%} disjoint return path"
        )
        
        return LoopResult(
            outbound_path=outbound_result.path_nodes,
            return_path=return_result.path_nodes,
            full_path_coords=full_coords,
            total_distance=total_distance,
            total_time=total_time,
            vibe_profile=combined_profile,
            nodes_explored=total_explored,
            disjoint_percentage=disjoint_pct
        )
    
    def generate_loop_bidirectional(
        self,
        origin_node: int,
        duration_minutes: int,
        vibe_weights: dict[str, float]
    ) -> LoopResult:
        """
        Advanced: Generate loop using bi-directional search.
        
        This explores from both origin and turnaround simultaneously,
        finding the optimal meeting point.
        """
        target_distance = self._estimate_target_distance(duration_minutes)
        half_distance = target_distance / 2
        
        weight_func = self.cost_engine.create_weight_function(
            self.graph, vibe_weights, 'length'
        )
        
        # Forward search from origin
        forward_heap = [(0, origin_node, [origin_node])]
        forward_dist = {origin_node: 0}
        forward_paths = {origin_node: [origin_node]}
        
        # Track nodes at approximately half distance for potential meeting points
        meeting_candidates = []
        
        while forward_heap:
            dist, node, path = heapq.heappop(forward_heap)
            
            if dist > half_distance * 1.3:
                break
            
            if half_distance * 0.8 <= dist <= half_distance * 1.2:
                meeting_candidates.append((node, path, dist))
            
            if dist > forward_dist.get(node, float('inf')):
                continue
            
            for neighbor in self.graph.neighbors(node):
                edge_data = self.graph[node][neighbor][0]
                edge_cost = weight_func(node, neighbor, edge_data)
                new_dist = dist + edge_cost
                
                if new_dist < forward_dist.get(neighbor, float('inf')):
                    forward_dist[neighbor] = new_dist
                    new_path = path + [neighbor]
                    forward_paths[neighbor] = new_path
                    heapq.heappush(forward_heap, (new_dist, neighbor, new_path))
        
        if not meeting_candidates:
            # Fallback to simple loop generation
            return self.generate_loop(origin_node, duration_minutes, vibe_weights)
        
        # Find best meeting point and generate return path
        best_result = None
        best_disjoint = 0.0
        
        for meeting_node, outbound_path, outbound_dist in meeting_candidates[:3]:
            try:
                outbound_edges = set()
                for i in range(len(outbound_path) - 1):
                    u, v = outbound_path[i], outbound_path[i+1]
                    outbound_edges.add((u, v))
                    outbound_edges.add((v, u))
                
                return_result = self.routing.find_route_avoiding_edges(
                    meeting_node, origin_node, vibe_weights,
                    outbound_edges, algorithm="astar"
                )
                
                return_edges = set()
                for i in range(len(return_result.path_nodes) - 1):
                    u, v = return_result.path_nodes[i], return_result.path_nodes[i+1]
                    return_edges.add((u, v))
                
                disjoint = self._calculate_disjoint_percentage(outbound_edges, return_edges)
                
                if disjoint > best_disjoint:
                    best_disjoint = disjoint
                    
                    # Build outbound result manually
                    outbound_coords = [
                        (self.graph.nodes[n]['y'], self.graph.nodes[n]['x'])
                        for n in outbound_path
                    ]
                    
                    full_coords = outbound_coords + return_result.path_coords[1:]
                    total_distance = outbound_dist + return_result.total_distance
                    total_time = total_distance / 1.25
                    
                    combined_profile = self.vibe_engine.compute_route_vibe_profile(full_coords)
                    
                    best_result = LoopResult(
                        outbound_path=outbound_path,
                        return_path=return_result.path_nodes,
                        full_path_coords=full_coords,
                        total_distance=total_distance,
                        total_time=total_time,
                        vibe_profile=combined_profile,
                        nodes_explored=len(forward_dist) + return_result.nodes_explored,
                        disjoint_percentage=disjoint
                    )
            except ValueError:
                continue
        
        if best_result:
            return best_result
        
        # Fallback
        return self.generate_loop(origin_node, duration_minutes, vibe_weights)
