"""
Business Need Profile (BNP) Markdown Parser.

Parses human-readable markdown BNP files into structured profiles.
Enables organizations to define agent evaluation needs without technical complexity.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
import re
import yaml
from datetime import datetime

from agentfit.bnp.schema import (
    BNPProfile,
    AgentRequirement,
    DimensionWeight,
    AgentDomain,
    TaskComplexity,
)


class BNPParser:
    """Parse Business Need Profiles from markdown format."""

    parse = staticmethod(lambda content: BNPParser.parse_markdown(content))
    
    @staticmethod
    def parse_markdown(content: str) -> BNPProfile:
        """
        Parse markdown BNP content into a structured profile.
        
        Format:
        ```
        # Profile: <name>
        
        ## Metadata
        - Organization: <org>
        - Domain: <domain>
        - Description: <desc>
        
        ## Agent Requirements
        - <capability>: <description> (required|optional, priority: low|medium|high|critical)
        
        ## Evaluation Setup
        - Complexity: <simple|moderate|complex|expert>
        - Dimensions:
          - task_competence: 0.5
          - tool_use: 0.5
        
        ## Constraints
        - Max Latency: <ms>
        - Max Errors per Task: <n>
        
        ## Compliance
        - <requirement1>
        - <requirement2>
        ```
        """
        profile = BNPProfile()
        profile.created_at = datetime.utcnow().isoformat()
        profile.updated_at = datetime.utcnow().isoformat()
        
        # Extract YAML frontmatter if present
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1]) or {}
                content = parts[2]
                _apply_frontmatter(profile, frontmatter)
        
        # Parse markdown sections
        sections = BNPParser._split_sections(content)
        
        for section_name, section_content in sections.items():
            if section_name == "metadata":
                BNPParser._parse_metadata(section_content, profile)
            elif section_name == "agent requirements":
                BNPParser._parse_requirements(section_content, profile)
            elif section_name == "evaluation setup":
                BNPParser._parse_evaluation_setup(section_content, profile)
            elif section_name == "constraints":
                BNPParser._parse_constraints(section_content, profile)
            elif section_name == "compliance":
                BNPParser._parse_compliance(section_content, profile)
        
        # Extract profile name from header if not already set
        header_match = re.search(r"^#\s+Profile:\s+(.+)$", content, re.MULTILINE)
        if header_match and not profile.name:
            profile.name = header_match.group(1).strip()
        
        # Validate
        profile.validate()
        return profile
    
    @staticmethod
    def parse_file(filepath: str) -> BNPProfile:
        """Parse BNP from a markdown file."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"BNP file not found: {filepath}")
        
        content = path.read_text(encoding="utf-8")
        return BNPParser.parse_markdown(content)
    
    @staticmethod
    def _split_sections(content: str) -> Dict[str, str]:
        """Split markdown into sections by ## headers."""
        sections = {}
        current_section = None
        current_content = []
        
        for line in content.split("\n"):
            if line.startswith("##"):
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = line.replace("##", "").strip().lower()
                current_content = []
            elif current_section:
                current_content.append(line)
        
        if current_section:
            sections[current_section] = "\n".join(current_content).strip()
        
        return sections
    
    @staticmethod
    def _parse_metadata(content: str, profile: BNPProfile) -> None:
        """Parse metadata section."""
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            if line.startswith("- Organization:"):
                profile.organization = line.split(":", 1)[1].strip()
            elif line.startswith("- Domain:"):
                domain_str = line.split(":", 1)[1].strip().lower()
                try:
                    profile.agent_domain = AgentDomain(domain_str)
                except ValueError:
                    profile.agent_domain = AgentDomain.GENERAL
            elif line.startswith("- Description:"):
                profile.description = line.split(":", 1)[1].strip()
            elif line.startswith("- Agent Name:"):
                profile.agent_name = line.split(":", 1)[1].strip()
            elif line.startswith("- Tags:"):
                tags_str = line.split(":", 1)[1].strip()
                profile.tags = [t.strip() for t in tags_str.split(",")]
    
    @staticmethod
    def _parse_requirements(content: str, profile: BNPProfile) -> None:
        """Parse agent requirements section."""
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            if line.startswith("- "):
                req_text = line[2:]
                
                # Parse: <capability>: <description> (required|optional) [priority: <level>]
                # Example: Tool Use: Can call APIs and process responses (required, priority: high)
                match = re.match(
                    r"(.+?):\s+(.+?)\s*\(\s*(required|optional)(?:,\s*priority:\s*(\w+))?\s*\)",
                    req_text
                )
                
                if match:
                    capability, description, req_str, priority = match.groups()
                    req = AgentRequirement(
                        capability=capability.strip(),
                        description=description.strip(),
                        required=req_str.lower() == "required",
                        priority=priority.lower() if priority else "medium"
                    )
                    profile.requirements.append(req)
                    
                    if req.required:
                        profile.critical_capabilities.append(req.capability)
    
    @staticmethod
    def _parse_evaluation_setup(content: str, profile: BNPProfile) -> None:
        """Parse evaluation configuration section."""
        in_dimensions = False
        
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("- Complexity:"):
                complexity_str = line.split(":", 1)[1].strip().lower()
                try:
                    profile.task_complexity = TaskComplexity(complexity_str)
                except ValueError:
                    profile.task_complexity = TaskComplexity.MODERATE
            
            elif line.startswith("- Dimensions:"):
                in_dimensions = True
            elif in_dimensions and line.startswith("- "):
                # Parse: dimension_name: weight
                parts = line[2:].split(":")
                if len(parts) == 2:
                    dim_name = parts[0].strip()
                    try:
                        weight = float(parts[1].strip())
                        profile.evaluation_dimensions.append(
                            DimensionWeight(dimension=dim_name, weight=weight)
                        )
                    except ValueError:
                        pass
            elif in_dimensions and not line.startswith("- "):
                in_dimensions = False
    
    @staticmethod
    def _parse_constraints(content: str, profile: BNPProfile) -> None:
        """Parse constraints section."""
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            if line.startswith("- Max Latency:"):
                latency_str = line.split(":", 1)[1].strip().lower()
                try:
                    profile.max_latency_ms = int(latency_str.replace("ms", "").strip())
                except ValueError:
                    pass
            elif line.startswith("- Max Errors"):
                errors_str = line.split(":", 1)[1].strip()
                try:
                    profile.max_errors_per_task = int(errors_str.split()[0])
                except (ValueError, IndexError):
                    pass
    
    @staticmethod
    def _parse_compliance(content: str, profile: BNPProfile) -> None:
        """Parse compliance section."""
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                requirement = line[2:].strip()
                profile.compliance_requirements.append(requirement)


def _apply_frontmatter(profile: BNPProfile, frontmatter: Dict[str, Any]) -> None:
    """Apply YAML frontmatter to profile."""
    if "name" in frontmatter:
        profile.name = frontmatter["name"]
    if "organization" in frontmatter:
        profile.organization = frontmatter["organization"]
    if "description" in frontmatter:
        profile.description = frontmatter["description"]
    if "domain" in frontmatter:
        try:
            profile.agent_domain = AgentDomain(frontmatter["domain"].lower())
        except ValueError:
            pass
    if "tags" in frontmatter:
        profile.tags = frontmatter.get("tags", [])
