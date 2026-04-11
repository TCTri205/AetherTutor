import re
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ParsedNote(BaseModel):
    title: str
    content: str
    frontmatter: Dict[str, Any] = {}
    links: List[str] = []
    tags: List[str] = []
    file_path: Optional[str] = None
    filename: str = ""  # Filename without extension (for wiki-link resolution)

class MarkdownParser:
    """
    Parser for Obsidian-flavored Markdown files.
    Extracts frontmatter, wiki-links, and tags.
    """
    
    # Wiki-links: [[Note Name]] or [[Note Name|Alias]]. Exclude ![[Image]]
    WIKI_LINK_PATTERN = re.compile(r'(?<!\!)\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]')
    
    # Tags: #tag (must start with letter, can contain numbers, hyphens, underscores)
    TAG_PATTERN = re.compile(r'(?<!\S)#([a-zA-Z][a-zA-Z0-9/_-]*)')
    
    # Frontmatter: --- \n (YAML) \n ---
    FRONTMATTER_PATTERN = re.compile(r'^\s*---\s*\n(.*?)\n---\s*\n', re.DOTALL)

    def parse_file(self, file_path: Path) -> ParsedNote:
        """Parse a markdown file and return a ParsedNote object."""
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Fallback for other encodings if necessary
            content = file_path.read_text(encoding='latin-1')

        note = self.parse_content(content, title=file_path.stem, file_path=str(file_path))
        # Set filename after parsing (for wiki-link resolution)
        note.filename = file_path.stem
        return note

    def parse_content(self, content: str, title: str, file_path: Optional[str] = None) -> ParsedNote:
        """Parse markdown content string."""
        frontmatter = {}
        clean_content = content

        # 1. Extract Frontmatter
        fm_match = self.FRONTMATTER_PATTERN.match(content)
        if fm_match:
            try:
                fm_text = fm_match.group(1)
                frontmatter = yaml.safe_load(fm_text) or {}
                clean_content = content[fm_match.end():]
            except Exception:
                pass # Ignore malformed YAML

        # 0. Extract Title from H1 if present
        h1_match = re.search(r'^#\s+(.+)$', clean_content, re.MULTILINE)
        if h1_match:
            title = h1_match.group(1).strip()

        # 2. Extract Wiki-links
        # We take group 1 (the target note name)
        links = []
        for match in self.WIKI_LINK_PATTERN.finditer(clean_content):
            links.append(match.group(1).strip())
        
        # Deduplicate links while preserving order
        seen_links = set()
        unique_links = []
        for link in links:
            if link not in seen_links:
                unique_links.append(link)
                seen_links.add(link)

        # 3. Extract Tags
        tags = []
        # Check both content and frontmatter for tags
        for match in self.TAG_PATTERN.finditer(clean_content):
            tags.append(match.group(1).lower())
            
        if 'tags' in frontmatter:
            if isinstance(frontmatter['tags'], list):
                tags.extend([str(t).lower() for t in frontmatter['tags']])
            elif isinstance(frontmatter['tags'], str):
                tags.append(frontmatter['tags'].lower())

        # Normalize tags
        normalized_tags = list(set([t.strip('#') for t in tags if t]))

        return ParsedNote(
            title=title,
            content=clean_content,
            frontmatter=frontmatter,
            links=unique_links,
            tags=normalized_tags,
            file_path=file_path
        )
