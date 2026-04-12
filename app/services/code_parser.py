"""
Code Parser Service - Parse source code files and extract entities/relations.

Supports:
- Python (.py) via AST module
- JavaScript (.js) via regex patterns
- TypeScript (.ts) via regex patterns

Extracts:
- Classes, functions, methods
- Imports, dependencies
- Decorators, docstrings
- Relations: CONTAINS, IMPORTS, CALLS, INHERITS
"""

import ast
import logging
from pathlib import Path
from typing import Any

from app.schemas.lightrag import ExtractedEntity, EntityRelation, ExtractionResult

logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE = 500 * 1024  # 500KB
MAX_LINES = 2000

CODE_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.mjs'}
PYTHON_EXTENSIONS = {'.py'}
JAVASCRIPT_EXTENSIONS = {'.js', '.jsx', '.mjs'}
TYPESCRIPT_EXTENSIONS = {'.ts', '.tsx'}


class CodeParserError(Exception):
    """Base exception for code parser errors."""
    pass


class FileSizeError(CodeParserError):
    """File exceeds size or line limit."""
    pass


class CodeParser:
    """
    Parse source code files and extract entities/relations for graph building.
    
    Usage:
        parser = CodeParser()
        result = parser.parse_file(Path("example.py"))
    """

    def __init__(self):
        self.file_path: Path | None = None
        self.source_code: str = ""
        self.language: str = ""

    def parse_file(self, file_path: Path) -> ExtractionResult:
        """
        Parse a source code file and extract entities/relations.
        
        Args:
            file_path: Path to the source code file
            
        Returns:
            ExtractionResult with entities and relations
            
        Raises:
            FileSizeError: If file exceeds limits
            CodeParserError: If parsing fails
        """
        self.file_path = file_path
        self._validate_file(file_path)
        self.source_code = file_path.read_text(encoding='utf-8')
        self.language = self._detect_language(file_path)
        
        logger.info(f"Parsing {self.language} file: {file_path.name} ({len(self.source_code)} chars)")
        
        try:
            if self.language == "python":
                return self._parse_python()
            elif self.language in ("javascript", "typescript"):
                return self._parse_javascript()
            else:
                raise CodeParserError(f"Unsupported language for file: {file_path.name}")
        except CodeParserError:
            raise
        except Exception as e:
            logger.error(f"Failed to parse {file_path.name}: {e}")
            raise CodeParserError(f"Parser error: {str(e)}") from e

    def parse_code_string(self, code: str, language: str = "python") -> ExtractionResult:
        """
        Parse code from a string (for code snippets, clipboard, etc.).
        
        Args:
            code: Source code string
            language: Language hint (python, javascript, typescript)
            
        Returns:
            ExtractionResult with entities and relations
        """
        self.source_code = code
        self.language = language.lower()
        self.file_path = None
        
        try:
            if self.language == "python":
                return self._parse_python()
            elif self.language in ("javascript", "typescript"):
                return self._parse_javascript()
            else:
                raise CodeParserError(f"Unsupported language: {language}")
        except CodeParserError:
            raise
        except Exception as e:
            logger.error(f"Failed to parse code string: {e}")
            raise CodeParserError(f"Parser error: {str(e)}") from e

    def _validate_file(self, file_path: Path) -> None:
        """Validate file size and line count."""
        if not file_path.exists():
            raise FileSizeError(f"File not found: {file_path}")
        
        file_size = file_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            raise FileSizeError(
                f"File too large: {file_size / 1024:.1f}KB > {MAX_FILE_SIZE / 1024:.0f}KB limit"
            )
        
        line_count = sum(1 for _ in file_path.open('r', encoding='utf-8'))
        if line_count > MAX_LINES:
            raise FileSizeError(
                f"File too many lines: {line_count} > {MAX_LINES} limit"
            )

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        ext = file_path.suffix.lower()
        
        if ext in PYTHON_EXTENSIONS:
            return "python"
        elif ext in TYPESCRIPT_EXTENSIONS:
            return "typescript"
        elif ext in JAVASCRIPT_EXTENSIONS:
            return "javascript"
        else:
            raise CodeParserError(f"Unsupported file extension: {ext}")

    def _parse_python(self) -> ExtractionResult:
        """Parse Python source code using AST module."""
        try:
            tree = ast.parse(self.source_code)
        except SyntaxError as e:
            raise CodeParserError(f"Python syntax error: {e}") from e
        
        entities: list[ExtractedEntity] = []
        relations: list[EntityRelation] = []
        
        # Extract module name
        module_name = self.file_path.stem if self.file_path else "unknown"
        entities.append(ExtractedEntity(
            name=f"Module:{module_name}",
            entity_type="Module",
            description=f"Python module: {module_name}",
            confidence=1.0
        ))
        
        # Track imports
        imported_modules: list[str] = []
        
        # Walk AST nodes
        for node in ast.walk(tree):
            # Import statements
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.append(alias.name)
                    entities.append(ExtractedEntity(
                        name=f"Module:{alias.name}",
                        entity_type="Module",
                        description=f"Imported module: {alias.name}",
                        confidence=0.9
                    ))
                    relations.append(EntityRelation(
                        source=f"Module:{module_name}",
                        target=f"Module:{alias.name}",
                        relation_type="IMPORTS",
                        description=f"Module {module_name} imports {alias.name}"
                    ))
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.append(node.module)
                    entities.append(ExtractedEntity(
                        name=f"Module:{node.module}",
                        entity_type="Module",
                        description=f"Imported module: {node.module}",
                        confidence=0.9
                    ))
                    relations.append(EntityRelation(
                        source=f"Module:{module_name}",
                        target=f"Module:{node.module}",
                        relation_type="IMPORTS",
                        description=f"Module {module_name} imports from {node.module}"
                    ))
            
            # Class definitions
            elif isinstance(node, ast.ClassDef):
                class_name = f"Class:{node.name}"
                bases = [base.attr if isinstance(base, ast.Attribute) else base.id 
                        for base in node.bases if isinstance(base, (ast.Name, ast.Attribute))]
                
                description = node.name
                if bases:
                    description += f"({', '.join(bases)})"
                
                # Add docstring if present
                docstring = ast.get_docstring(node)
                if docstring:
                    description += f"\n\n{docstring[:200]}"
                
                entities.append(ExtractedEntity(
                    name=class_name,
                    entity_type="Class",
                    description=description.strip(),
                    confidence=1.0
                ))
                
                # CONTAINS relation: Module contains Class
                relations.append(EntityRelation(
                    source=f"Module:{module_name}",
                    target=class_name,
                    relation_type="CONTAINS",
                    description=f"Module {module_name} contains class {node.name}"
                ))
                
                # INHERITS relations
                for base in bases:
                    base_entity = f"Class:{base}"
                    entities.append(ExtractedEntity(
                        name=base_entity,
                        entity_type="Class",
                        description=f"Base class: {base}",
                        confidence=0.8
                    ))
                    relations.append(EntityRelation(
                        source=class_name,
                        target=base_entity,
                        relation_type="INHERITS",
                        description=f"{node.name} inherits from {base}"
                    ))
                
                # Methods inside class
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_name = f"Function:{node.name}.{item.name}"
                        description = f"Method {item.name}"
                        
                        # Decorators
                        decorators = [d.attr if isinstance(d, ast.Attribute) else d.id 
                                    for d in item.decorator_list if isinstance(d, (ast.Name, ast.Attribute))]
                        if decorators:
                            description += f"\nDecorators: {', '.join(decorators)}"
                        
                        # Docstring
                        method_doc = ast.get_docstring(item)
                        if method_doc:
                            description += f"\n\n{method_doc[:200]}"
                        
                        entities.append(ExtractedEntity(
                            name=method_name,
                            entity_type="Function",
                            description=description.strip(),
                            confidence=1.0
                        ))
                        
                        relations.append(EntityRelation(
                            source=class_name,
                            target=method_name,
                            relation_type="CONTAINS",
                            description=f"Class {node.name} contains method {item.name}"
                        ))
            
            # Top-level function definitions
            elif isinstance(node, ast.FunctionDef):
                # Skip if already handled as method
                if self._is_nested_in_class(node, tree):
                    continue
                
                func_name = f"Function:{node.name}"
                description = f"Function {node.name}"
                
                # Decorators
                decorators = [d.attr if isinstance(d, ast.Attribute) else d.id 
                            for d in node.decorator_list if isinstance(d, (ast.Name, ast.Attribute))]
                if decorators:
                    description += f"\nDecorators: {', '.join(decorators)}"
                
                # Docstring
                docstring = ast.get_docstring(node)
                if docstring:
                    description += f"\n\n{docstring[:200]}"
                
                entities.append(ExtractedEntity(
                    name=func_name,
                    entity_type="Function",
                    description=description.strip(),
                    confidence=1.0
                ))
                
                relations.append(EntityRelation(
                    source=f"Module:{module_name}",
                    target=func_name,
                    relation_type="CONTAINS",
                    description=f"Module {module_name} contains function {node.name}"
                ))
                
                # Extract function calls
                call_relations = self._extract_python_calls(node, module_name)
                relations.extend(call_relations)
        
        # Deduplicate entities and relations
        entities = self._deduplicate_entities(entities)
        relations = self._deduplicate_relations(relations)
        
        return ExtractionResult(entities=entities, relations=relations)

    def _parse_javascript(self) -> ExtractionResult:
        """Parse JavaScript/TypeScript source code using regex patterns."""
        import re
        
        entities: list[ExtractedEntity] = []
        relations: list[EntityRelation] = []
        
        file_name = self.file_path.stem if self.file_path else "unknown"
        module_name = f"Module:{file_name}"
        
        entities.append(ExtractedEntity(
            name=module_name,
            entity_type="Module",
            description=f"{'TypeScript' if self.language == 'typescript' else 'JavaScript'} module: {file_name}",
            confidence=1.0
        ))
        
        lines = self.source_code.split('\n')
        
        # Track current class context
        current_class: str | None = None
        brace_depth = 0
        
        # Regex patterns
        import_pattern = re.compile(
            r'(?:import|require)\s*(?:{[^}]*}|\w+)?\s*(?:from\s*)?[\'"]([^\'"]+)[\'"]'
        )
        class_pattern = re.compile(
            r'(?:export\s+)?(?:default\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?'
        )
        function_pattern = re.compile(
            r'(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)'
        )
        method_pattern = re.compile(
            r'(?:async\s+)?(\w+)\s*\(.*?\)\s*(?::\s*\w+[\[\]]?)?\s*{'
        )
        arrow_function_pattern = re.compile(
            r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*(?::\s*[\w<>,\s]+)?\s*=>'
        )
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Skip comments and empty lines
            if stripped.startswith('//') or stripped.startswith('/*') or not stripped:
                continue
            
            # Track brace depth for scope
            brace_depth += stripped.count('{') - stripped.count('}')
            if brace_depth < 0:
                brace_depth = 0
            
            # Imports
            import_match = import_pattern.search(stripped)
            if import_match:
                imported_module = import_match.group(1)
                entities.append(ExtractedEntity(
                    name=f"Module:{imported_module}",
                    entity_type="Module",
                    description=f"Imported module: {imported_module}",
                    confidence=0.85
                ))
                relations.append(EntityRelation(
                    source=module_name,
                    target=f"Module:{imported_module}",
                    relation_type="IMPORTS",
                    description=f"Module {file_name} imports from {imported_module}"
                ))
            
            # Class definitions
            class_match = class_pattern.search(stripped)
            if class_match:
                class_name = f"Class:{class_match.group(1)}"
                current_class = class_match.group(1)
                
                description = class_match.group(1)
                if class_match.group(2):
                    base_class = class_match.group(2)
                    description += f" extends {base_class}"
                    base_entity = f"Class:{base_class}"
                    entities.append(ExtractedEntity(
                        name=base_entity,
                        entity_type="Class",
                        description=f"Base class: {base_class}",
                        confidence=0.8
                    ))
                    relations.append(EntityRelation(
                        source=class_name,
                        target=base_entity,
                        relation_type="INHERITS",
                        description=f"{current_class} extends {base_class}"
                    ))
                
                entities.append(ExtractedEntity(
                    name=class_name,
                    entity_type="Class",
                    description=description,
                    confidence=1.0
                ))
                relations.append(EntityRelation(
                    source=module_name,
                    target=class_name,
                    relation_type="CONTAINS",
                    description=f"Module {file_name} contains class {current_class}"
                ))
                continue
            
            # Reset class context when leaving class scope
            if current_class and brace_depth <= 1:
                current_class = None
            
            # Top-level functions
            func_match = function_pattern.search(stripped)
            if func_match and not current_class:
                func_name = f"Function:{func_match.group(1)}"
                entities.append(ExtractedEntity(
                    name=func_name,
                    entity_type="Function",
                    description=f"Function {func_match.group(1)}",
                    confidence=1.0
                ))
                relations.append(EntityRelation(
                    source=module_name,
                    target=func_name,
                    relation_type="CONTAINS",
                    description=f"Module {file_name} contains function {func_match.group(1)}"
                ))
                continue
            
            # Methods inside class
            if current_class:
                method_match = method_pattern.search(stripped)
                if method_match and method_match.group(1) not in ('if', 'for', 'while', 'switch'):
                    method_name = f"Function:{current_class}.{method_match.group(1)}"
                    entities.append(ExtractedEntity(
                        name=method_name,
                        entity_type="Function",
                        description=f"Method {method_match.group(1)}",
                        confidence=0.95
                    ))
                    relations.append(EntityRelation(
                        source=f"Class:{current_class}",
                        target=method_name,
                        relation_type="CONTAINS",
                        description=f"Class {current_class} contains method {method_match.group(1)}"
                    ))
                    continue
            
            # Arrow functions / const declarations
            arrow_match = arrow_function_pattern.search(stripped)
            if arrow_match and not current_class:
                func_name = f"Function:{arrow_match.group(1)}"
                entities.append(ExtractedEntity(
                    name=func_name,
                    entity_type="Function",
                    description=f"Arrow function {arrow_match.group(1)}",
                    confidence=0.9
                ))
                relations.append(EntityRelation(
                    source=module_name,
                    target=func_name,
                    relation_type="CONTAINS",
                    description=f"Module {file_name} contains function {arrow_match.group(1)}"
                ))
        
        # Deduplicate
        entities = self._deduplicate_entities(entities)
        relations = self._deduplicate_relations(relations)
        
        return ExtractionResult(entities=entities, relations=relations)

    def _extract_python_calls(self, func_node: ast.FunctionDef, module_name: str) -> list[EntityRelation]:
        """Extract function call relations from a function body."""
        relations = []
        func_name = f"Function:{func_node.name}"
        
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    target = f"Function:{node.func.id}"
                    relations.append(EntityRelation(
                        source=func_name,
                        target=target,
                        relation_type="CALLS",
                        description=f"{func_node.name} calls {node.func.id}"
                    ))
                elif isinstance(node.func, ast.Attribute):
                    target = f"Function:{node.func.attr}"
                    relations.append(EntityRelation(
                        source=func_name,
                        target=target,
                        relation_type="CALLS",
                        description=f"{func_node.name} calls {node.func.attr}"
                    ))
        
        return relations

    def _is_nested_in_class(self, func_node: ast.FunctionDef, tree: ast.Module) -> bool:
        """Check if a function is nested inside a class (to avoid double-processing)."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if item is func_node:
                        return True
        return False

    def _deduplicate_entities(self, entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
        """Remove duplicate entities by name."""
        seen: dict[str, ExtractedEntity] = {}
        for entity in entities:
            if entity.name not in seen:
                seen[entity.name] = entity
            else:
                # Keep the one with higher confidence
                if entity.confidence > seen[entity.name].confidence:
                    seen[entity.name] = entity
        return list(seen.values())

    def _deduplicate_relations(self, relations: list[EntityRelation]) -> list[EntityRelation]:
        """Remove duplicate relations by (source, target, relation_type)."""
        seen: set[tuple[str, str, str]] = set()
        unique: list[EntityRelation] = []
        
        for relation in relations:
            key = (relation.source, relation.target, relation.relation_type)
            if key not in seen:
                seen.add(key)
                unique.append(relation)
        
        return unique

    def get_code_snippet(self, file_path: Path | None = None, max_lines: int = 100) -> str:
        """
        Get code snippet from file (for storage in graph_entities.code_snippet).
        
        Args:
            file_path: Path to file (defaults to self.file_path)
            max_lines: Maximum lines to return
            
        Returns:
            Code snippet string
        """
        path = file_path or self.file_path
        if not path or not path.exists():
            return ""
        
        try:
            with path.open('r', encoding='utf-8') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line)
                
                snippet = ''.join(lines)
                if len(lines) == max_lines:
                    snippet += f"\n\n// ... truncated ({max_lines} lines shown)"
                
                return snippet
        except Exception as e:
            logger.warning(f"Failed to read code snippet: {e}")
            return ""


# Singleton instance for convenience
code_parser = CodeParser()
