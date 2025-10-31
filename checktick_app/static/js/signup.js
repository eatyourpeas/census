function updateOrgNameState() {
  const simpleRadio = document.querySelector(
    'input[name="account_type"][value="simple"]'
  );
  const orgRadio = document.querySelector(
    'input[name="account_type"][value="org"]'
  );
  const orgNameInput = document.getElementById("org-name-input");
  const orgNameContainer = document.getElementById("org-name-container");

  if (simpleRadio.checked) {
    // Hide organization name field for individual accounts
    orgNameContainer.style.display = "none";
    orgNameInput.removeAttribute("required");
    orgNameInput.value = ""; // Clear the input when hidden
  } else if (orgRadio.checked) {
    // Show organization name field for organization accounts
    orgNameContainer.style.display = "block";
    orgNameInput.setAttribute("required", "required");
  }

  // Update hidden form fields
  updateHiddenFields();
}

function updateHiddenFields() {
  const selectedAccountType = document.querySelector(
    'input[name="account_type"]:checked'
  ).value;
  const orgName = document.getElementById("org-name-input").value;

  // Update hidden fields for traditional form submission
  document.getElementById("selected-account-type").value = selectedAccountType;
  document.getElementById("selected-org-name").value = orgName;
}

function handleSSOSignup(provider) {
  const accountType = document.querySelector(
    'input[name="account_type"]:checked'
  ).value;
  const orgName = document.getElementById("org-name-input").value;

  // Validate organization name if org account is selected
  if (accountType === "org" && !orgName.trim()) {
    alert("Please enter an organization name for your organization account.");
    return;
  }

  // Store choices in sessionStorage for post-auth processing
  sessionStorage.setItem("signup_account_type", accountType);
  if (orgName && accountType === "org") {
    sessionStorage.setItem("signup_org_name", orgName);
  } else {
    sessionStorage.removeItem("signup_org_name");
  }

  // Redirect to OIDC with signup flag
  window.location.href = `/oidc/authenticate/?provider=${provider}&signup=true`;
}

// Set initial state when page loads
document.addEventListener("DOMContentLoaded", function () {
  updateOrgNameState();

  // Add event listeners to radio buttons
  const accountTypeRadios = document.querySelectorAll(
    'input[name="account_type"]'
  );
  accountTypeRadios.forEach((radio) => {
    radio.addEventListener("change", updateOrgNameState);
  });

  // Add event listener to org name input to update hidden field
  const orgNameInput = document.getElementById("org-name-input");
  if (orgNameInput) {
    orgNameInput.addEventListener("input", updateHiddenFields);
  }

  // Add event listeners to SSO buttons
  const googleBtn = document.getElementById("google-signup");
  const azureBtn = document.getElementById("azure-signup");

  if (googleBtn) {
    googleBtn.addEventListener("click", () => handleSSOSignup("google"));
  }

  if (azureBtn) {
    azureBtn.addEventListener("click", () => handleSSOSignup("azure"));
  }
});
