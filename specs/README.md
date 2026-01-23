# Spec-Kit Specifications

This directory contains the specification files for the Discharge Summary Generator repository. These specs are used to describe the repository's features, modules, and generation rules, enabling a spec-driven development workflow.

## File Format

### `main_spec.yaml`
- **project_name**: The name of the project.
- **description**: A brief description of the project.
- **owner**: The owner of the repository.
- **modules**: A list of modules in the repository, each with a name and description.
- **api_contracts**: Definitions of API endpoints, including methods, request bodies, and response bodies.
- **dev_tasks**: Common development tasks with their respective commands.
- **priority_features**: User stories and acceptance criteria for the most important features.
- **generation_rules**: Mapping of features to the files/modules that implement them.

## Usage

1. **Understand the Repository**: Read `main_spec.yaml` to get an overview of the repository's purpose and structure.
2. **Modify or Extend**: Update the spec file to add new features or modify existing ones.
3. **Generate Code**: Use Spec-Kit CLI to regenerate code based on the updated specs.