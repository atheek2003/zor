import unittest
import re

class TestRegexPatterns(unittest.TestCase):
    
    def test_file_parsing_regex(self):
        """Test that the regex pattern correctly parses file content"""
        # Sample response with correct formatting - notice the exact spacing
        files_response = """FILE: README.md
```
# Test Project

A simple test project.
```

FILE: setup.py
```
from setuptools import setup

setup(
    name="test_project",
    version="0.1.0",
)
```"""
        
        # The regex pattern from the original code
        file_matches = re.findall(r"FILE: (.+?)\n```(?:\w+)?\n(.+?)```", files_response, re.DOTALL)
        
        # Verify parsing worked
        self.assertEqual(len(file_matches), 2)
        self.assertEqual(file_matches[0][0], "README.md")
        self.assertTrue("# Test Project" in file_matches[0][1])
        self.assertEqual(file_matches[1][0], "setup.py")
        self.assertTrue("setup(" in file_matches[1][1])

    def test_project_type_extraction(self):
        """Test that the project type is correctly extracted"""
        # Sample response
        plan_response = """PROJECT_TYPE: Python CLI Application

MAIN_TECHNOLOGIES: Python, Typer, Rich

ARCHITECTURE: Command-line interface"""
        
        # Extract project type
        project_type_match = re.search(r"PROJECT_TYPE:\s*(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", 
                                       plan_response + "\n\n", re.DOTALL)
        
        # Verify extraction worked
        self.assertIsNotNone(project_type_match)
        project_type = project_type_match.group(1).strip()
        self.assertEqual(project_type, "Python CLI Application")
        
    def test_custom_regex_file_pattern(self):
        """Alternative regex pattern that might be more robust"""
        files_response = """FILE: README.md
```
# Test Project

A simple test project.
```

FILE: setup.py
```
from setuptools import setup

setup(
    name="test_project",
    version="0.1.0",
)
```"""
        
        # Alternative regex that may be more reliable
        file_matches = re.findall(r"FILE:\s*([^\n]+)(?:\n```(?:\w+)?\n)(.*?)(?:\n```)", files_response, re.DOTALL)
        
        # Verify parsing worked
        self.assertEqual(len(file_matches), 2)
        self.assertEqual(file_matches[0][0], "README.md")
        self.assertEqual(file_matches[1][0], "setup.py")

if __name__ == '__main__':
    unittest.main()
