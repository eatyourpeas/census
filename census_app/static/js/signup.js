function updateOrgNameState() {
  const simpleRadio = document.querySelector(
    'input[name="account_type"][value="simple"]'
  );
  const orgNameInput = document.getElementById("org-name-input");
  const orgNameLabel = document.getElementById("org-name-label");
  const orgNameContainer = document.getElementById("org-name-container");

  if (simpleRadio.checked) {
    // Disable input and grey out for simple user
    orgNameInput.disabled = true;
    orgNameLabel.classList.add("text-base-content/40");
    orgNameContainer.classList.add("opacity-50");
    orgNameInput.value = ""; // Clear the input when disabled
  } else {
    // Enable input for org account
    orgNameInput.disabled = false;
    orgNameLabel.classList.remove("text-base-content/40");
    orgNameContainer.classList.remove("opacity-50");
  }
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
});
