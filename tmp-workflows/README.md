These are pinned copies of the GitHub Actions workflows.

Why this exists:
- We cannot modify files under .github/workflows/ from this environment, so we created pinned copies here.

What changed:
- tmp-workflows/docker-build.yml: aquasecurity/trivy-action pinned from @master to @v0.24.0
- tmp-workflows/claude.yml: anthropics/claude-code-action pinned from @beta to @v1.0.0 (maintainers should update to a specific commit SHA for maximum supply-chain security)
- tmp-workflows/claude-code-review.yml: anthropics/claude-code-action pinned from @beta to @v1.0.0 (maintainers should update to a specific commit SHA for maximum supply-chain security)

Next steps (maintainers):
1) Manually move the files from tmp-workflows/ into .github/workflows/ in the repository root:
   - .github/workflows/docker-build.yml
   - .github/workflows/claude.yml
   - .github/workflows/claude-code-review.yml
2) Optionally replace the anthropics/claude-code-action@v1.0.0 tag with the immutable commit SHA of the desired release.
3) Verify the workflows run successfully in CI.
