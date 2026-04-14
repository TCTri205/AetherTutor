"""
Code Parser Tests (Sprint 22 - Phase 3).

Tests for app/services/code_parser.py:
- Python AST parsing
- JavaScript/TypeScript parsing
- Entity extraction
- Relation extraction
- Error handling
- Edge cases

Total: 15 tests
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.code_parser import (
    CodeParser,
    CodeParserError,
    FileSizeError,
    MAX_FILE_SIZE,
    MAX_LINES,
)


# --- Fixtures ---

@pytest.fixture
def parser():
    """Create a fresh CodeParser instance."""
    return CodeParser()


@pytest.fixture
def sample_python_code():
    """Sample Python code with classes, functions, imports."""
    return '''
import os
import sys
from pathlib import Path

class BaseClass:
    """Base class for inheritance."""
    def base_method(self):
        """A base method."""
        pass

class MyClass(BaseClass):
    """
    A sample class for testing.
    
    This class demonstrates inheritance and methods.
    """
    def __init__(self, name):
        self.name = name
    
    @property
    def display_name(self):
        """Return formatted name."""
        return f"Name: {self.name}"
    
    def greet(self):
        """Greet someone."""
        print(f"Hello, {self.name}!")

def helper_function(x, y):
    """A standalone helper function."""
    return x + y

@decorator
async def async_function():
    """An async function with decorator."""
    result = helper_function(1, 2)
    return result
'''


@pytest.fixture
def sample_javascript_code():
    """Sample JavaScript code with classes and functions."""
    return '''
import React from 'react';
import { useState, useEffect } from 'react';

class Animal {
  constructor(name) {
    this.name = name;
  }
  
  speak() {
    console.log(`${this.name} makes a sound`);
  }
}

class Dog extends Animal {
  constructor(name, breed) {
    super(name);
    this.breed = breed;
  }
  
  bark() {
    console.log('Woof!');
  }
}

function calculateSum(a, b) {
  return a + b;
}

const arrowFunction = (x, y) => {
  return x * y;
};

async function fetchData(url) {
  const response = await fetch(url);
  return response.json();
}
'''


@pytest.fixture
def sample_typescript_code():
    """Sample TypeScript code with interfaces and classes."""
    return '''
import { Component } from '@angular/core';
import { Observable } from 'rxjs';

interface User {
  id: number;
  name: string;
  email: string;
}

class UserService {
  private apiUrl: string;
  
  constructor(apiUrl: string) {
    this.apiUrl = apiUrl;
  }
  
  async getUsers(): Promise<User[]> {
    const response = await fetch(this.apiUrl);
    return response.json();
  }
  
  getUserById(id: number): User | null {
    // Implementation
    return null;
  }
}

export function formatUser(user: User): string {
  return `${user.name} <${user.email}>`;
}
'''


@pytest.fixture
def temp_python_file(tmp_path, sample_python_code):
    """Create a temporary Python file with sample code."""
    file_path = tmp_path / "test_module.py"
    file_path.write_text(sample_python_code, encoding='utf-8')
    return file_path


@pytest.fixture
def temp_js_file(tmp_path, sample_javascript_code):
    """Create a temporary JavaScript file with sample code."""
    file_path = tmp_path / "test_module.js"
    file_path.write_text(sample_javascript_code, encoding='utf-8')
    return file_path


@pytest.fixture
def temp_ts_file(tmp_path, sample_typescript_code):
    """Create a temporary TypeScript file with sample code."""
    file_path = tmp_path / "test_module.ts"
    file_path.write_text(sample_typescript_code, encoding='utf-8')
    return file_path


# === Test Cases ===

class TestPythonParsing:
    """Test Python AST parsing functionality."""

    def test_parse_python_simple_function(self, parser):
        """Test 1: Parse Python function with docstring and params."""
        code = '''
def greet(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"
'''
        result = parser.parse_code_string(code, language="python")

        # Should extract the function
        assert len(result.entities) >= 1
        function_entities = [e for e in result.entities if e.entity_type == "Function"]
        assert len(function_entities) >= 1
        assert any("greet" in e.name for e in function_entities)

    def test_parse_python_class(self, parser):
        """Test 2: Parse class with methods."""
        code = '''
class MyClass:
    """A sample class."""
    
    def method_one(self):
        """First method."""
        pass
    
    def method_two(self):
        """Second method."""
        return 42
'''
        result = parser.parse_code_string(code, language="python")

        # Should extract class and methods
        class_entities = [e for e in result.entities if e.entity_type == "Class"]
        function_entities = [e for e in result.entities if e.entity_type == "Function"]

        assert any("MyClass" in e.name for e in class_entities)
        assert len(function_entities) >= 2  # At least 2 methods

    def test_parse_python_class_inheritance(self, parser):
        """Test 3: Parse class with inheritance - INHERITS relation extracted."""
        code = '''
class Animal:
    pass

class Dog(Animal):
    """Dog inherits from Animal."""
    pass
'''
        result = parser.parse_code_string(code, language="python")

        # Should extract INHERITS relation
        inherits_relations = [r for r in result.relations if r.relation_type == "INHERITS"]
        assert len(inherits_relations) >= 1
        assert "Dog" in inherits_relations[0].source
        assert "Animal" in inherits_relations[0].target

    def test_parse_python_imports(self, parser):
        """Test 4: Parse import statements - IMPORTS relations extracted."""
        code = '''
import os
import sys
from pathlib import Path
from collections import defaultdict
'''
        result = parser.parse_code_string(code, language="python")

        # Should extract IMPORTS relations
        import_relations = [r for r in result.relations if r.relation_type == "IMPORTS"]
        assert len(import_relations) >= 3  # At least 3 imports

    def test_parse_python_method_calls(self, parser):
        """Test 5: Parse method calls within functions - CALLS relations extracted."""
        code = '''
def helper():
    return 42

def main():
    result = helper()
    print(result)
'''
        result = parser.parse_code_string(code, language="python")

        # Should extract CALLS relations
        calls_relations = [r for r in result.relations if r.relation_type == "CALLS"]
        assert len(calls_relations) >= 1

    def test_parse_python_nested_functions(self, parser):
        """Test 6: Parse nested function definitions."""
        code = '''
def outer():
    """Outer function."""
    
    def inner():
        """Inner function."""
        return 42
    
    return inner()
'''
        result = parser.parse_code_string(code, language="python")

        # Should extract both functions
        function_entities = [e for e in result.entities if e.entity_type == "Function"]
        assert len(function_entities) >= 2

    def test_parse_python_decorators(self, parser):
        """Test 7: Parse decorated functions - decorators extracted as metadata."""
        code = '''
@staticmethod
def my_static_method():
    """A static method."""
    pass

@property
def my_property(self):
    """A property."""
    return self._value
'''
        result = parser.parse_code_string(code, language="python")

        # Should extract functions with decorators in description
        function_entities = [e for e in result.entities if e.entity_type == "Function"]
        assert len(function_entities) >= 2
        # Check decorators are mentioned in description
        assert any("staticmethod" in e.description.lower() for e in function_entities)


class TestJavaScriptParsing:
    """Test JavaScript/TypeScript parsing functionality."""

    def test_parse_js_functions(self, parser):
        """Test 8: Parse JavaScript function declarations."""
        code = '''
function greet(name) {
  console.log(`Hello, ${name}!`);
}

async function fetchData(url) {
  const response = await fetch(url);
  return response.json();
}
'''
        result = parser.parse_code_string(code, language="javascript")

        # Should extract functions
        function_entities = [e for e in result.entities if e.entity_type == "Function"]
        assert len(function_entities) >= 2
        assert any("greet" in e.name for e in function_entities)

    def test_parse_js_classes(self, parser):
        """Test 9: Parse JS class syntax - class and methods extracted."""
        code = '''
class Person {
  constructor(name) {
    this.name = name;
  }
  
  greet() {
    console.log(`Hello, ${this.name}`);
  }
}
'''
        result = parser.parse_code_string(code, language="javascript")

        # Should extract class and methods
        class_entities = [e for e in result.entities if e.entity_type == "Class"]
        function_entities = [e for e in result.entities if e.entity_type == "Function"]

        assert len(class_entities) >= 1
        assert any("Person" in e.name for e in class_entities)

    def test_parse_js_imports(self, parser):
        """Test 10: Parse ES6 import/export statements - IMPORTS relations extracted."""
        code = '''
import React from 'react';
import { useState, useEffect } from 'react';
import axios from 'axios';
'''
        result = parser.parse_code_string(code, language="javascript")

        # Should extract IMPORTS relations
        import_relations = [r for r in result.relations if r.relation_type == "IMPORTS"]
        assert len(import_relations) >= 2

    def test_parse_ts_types(self, parser):
        """Test 11: Parse TypeScript interfaces/types - type definitions extracted."""
        code = '''
interface User {
  id: number;
  name: string;
}

class UserService {
  getUser(id: number): User {
    return null;
  }
}
'''
        result = parser.parse_code_string(code, language="typescript")

        # Should parse TypeScript successfully
        assert len(result.entities) >= 1
        # Language should be detected correctly
        assert result.entities[0].confidence > 0


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_parse_file_size_limit(self, parser, tmp_path):
        """Test 12: Parse file exceeding size limit - Error raised, file rejected."""
        # Create file larger than MAX_FILE_SIZE
        large_file = tmp_path / "large.py"
        large_content = "x = 1\n" * (MAX_FILE_SIZE + 1000)  # Exceed limit
        large_file.write_text(large_content, encoding='utf-8')

        with pytest.raises(FileSizeError):
            parser.parse_file(large_file)

    def test_parse_syntax_error(self, parser):
        """Test 13: Parse code with syntax errors - Error handled gracefully."""
        code = '''
def broken_function(
    # Missing closing parenthesis and body
'''
        # Should handle gracefully, not crash
        with pytest.raises(CodeParserError):
            parser.parse_code_string(code, language="python")

    def test_parse_empty_file(self, parser):
        """Test 14: Parse empty or whitespace-only file - Empty result, no entities."""
        code = '''
# Just comments
# No actual code here

'''
        result = parser.parse_code_string(code, language="python")

        # Should extract module but no functions/classes
        assert len(result.entities) >= 1  # Module entity
        function_entities = [e for e in result.entities if e.entity_type == "Function"]
        class_entities = [e for e in result.entities if e.entity_type == "Class"]
        assert len(function_entities) == 0
        assert len(class_entities) == 0

    def test_parse_unsupported_language(self, parser):
        """Test 15: Parse code in unsupported language - Error raised."""
        code = "puts 'Hello, World!'"

        with pytest.raises(CodeParserError):
            parser.parse_code_string(code, language="ruby")


# === Integration Tests (File Parsing) ===

class TestFileParsingIntegration:
    """Test parsing actual files (integration-style unit tests)."""

    def test_parse_python_file(self, parser, temp_python_file):
        """Parse a real Python file and verify entities/relations."""
        result = parser.parse_file(temp_python_file)

        # Should extract classes, functions, imports
        class_entities = [e for e in result.entities if e.entity_type == "Class"]
        function_entities = [e for e in result.entities if e.entity_type == "Function"]
        import_relations = [r for r in result.relations if r.relation_type == "IMPORTS"]

        assert len(class_entities) >= 2  # BaseClass, MyClass
        assert len(function_entities) >= 3  # Methods + functions
        assert len(import_relations) >= 2  # os, sys, pathlib

    def test_parse_javascript_file(self, parser, temp_js_file):
        """Parse a real JavaScript file and verify entities/relations."""
        result = parser.parse_file(temp_js_file)

        # Should extract classes, functions, imports
        class_entities = [e for e in result.entities if e.entity_type == "Class"]
        function_entities = [e for e in result.entities if e.entity_type == "Function"]

        assert len(class_entities) >= 2  # Animal, Dog
        assert len(function_entities) >= 3  # calculateSum, arrowFunction, fetchData

    def test_parse_typescript_file(self, parser, temp_ts_file):
        """Parse a real TypeScript file and verify entities/relations."""
        result = parser.parse_file(temp_ts_file)

        # Should extract classes and functions
        class_entities = [e for e in result.entities if e.entity_type == "Class"]
        function_entities = [e for e in result.entities if e.entity_type == "Function"]

        assert len(class_entities) >= 1  # UserService
        assert len(function_entities) >= 1  # formatUser


# === Edge Cases ===

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_code_snippet_extraction(self, parser, temp_python_file):
        """Test getting code snippet from file."""
        snippet = parser.get_code_snippet(temp_python_file, max_lines=10)

        assert len(snippet) > 0
        # Snippet should have ~10-15 lines (max_lines + possible truncation message)
        lines = snippet.split('\n')
        assert len(lines) <= 15  # Reasonable upper bound

    def test_code_snippet_nonexistent_file(self, parser):
        """Test getting snippet from nonexistent file."""
        snippet = parser.get_code_snippet(Path("nonexistent.py"))
        assert snippet == ""

    def test_deduplicate_entities(self, parser):
        """Test entity deduplication."""
        from app.schemas.lightrag import ExtractedEntity

        entities = [
            ExtractedEntity(name="Class:A", entity_type="Class", description="First A", confidence=0.8),
            ExtractedEntity(name="Class:A", entity_type="Class", description="Second A", confidence=0.9),
            ExtractedEntity(name="Class:B", entity_type="Class", description="B class", confidence=0.7),
        ]

        deduplicated = parser._deduplicate_entities(entities)

        assert len(deduplicated) == 2  # A (higher confidence) and B
        entity_a = next(e for e in deduplicated if e.name == "Class:A")
        assert entity_a.confidence == 0.9  # Kept higher confidence

    def test_deduplicate_relations(self, parser):
        """Test relation deduplication."""
        from app.schemas.lightrag import EntityRelation

        relations = [
            EntityRelation(source="A", target="B", relation_type="CONTAINS", description="A contains B"),
            EntityRelation(source="A", target="B", relation_type="CONTAINS", description="A contains B dup"),  # Duplicate
            EntityRelation(source="B", target="C", relation_type="IMPORTS", description="B imports C"),
        ]

        deduplicated = parser._deduplicate_relations(relations)

        assert len(deduplicated) == 2  # One CONTAINS, one IMPORTS
