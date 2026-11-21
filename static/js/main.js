// AcxiomCRM Client-Side Validation and UI Interactions

document.addEventListener('DOMContentLoaded', function () {
  // 1. Mobile Sidebar Toggle
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebar = document.querySelector('.sidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', function () {
      sidebar.classList.toggle('show');
    });
  }

  // 2. Auto-dismiss Alert messages after 5s
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });

  // 3. Form Validation Framework (Client-side validation)
  const forms = document.querySelectorAll('.needs-validation');

  Array.from(forms).forEach(function (form) {
    form.addEventListener('submit', function (event) {
      let isValid = true;

      // Custom rule: Phone format validation
      const phoneInput = form.querySelector('input[name="phone"]');
      if (phoneInput && phoneInput.value.trim() !== '') {
        const cleanPhone = phoneInput.value.replace(/[\s\-\(\)\+]/g, '');
        if (!/^\d{10,15}$/.test(cleanPhone)) {
          phoneInput.setCustomValidity('Enter a valid phone number (10 to 15 digits).');
          isValid = false;
        } else {
          phoneInput.setCustomValidity('');
        }
      }

      // Custom rule: Opportunity Amount > 0
      const amountInput = form.querySelector('input[name="amount"], input[name="opportunity_amount"]');
      if (amountInput && amountInput.value !== '') {
        const val = parseFloat(amountInput.value);
        if (isNaN(val) || val <= 0) {
          amountInput.setCustomValidity('Opportunity Amount must be greater than 0.');
          isValid = false;
        } else {
          amountInput.setCustomValidity('');
        }
      }

      // Custom rule: Probability 0 to 100
      const probInput = form.querySelector('input[name="probability"]');
      if (probInput && probInput.value !== '') {
        const prob = parseInt(probInput.value, 10);
        if (isNaN(prob) || prob < 0 || prob > 100) {
          probInput.setCustomValidity('Probability must be between 0 and 100.');
          isValid = false;
        } else {
          probInput.setCustomValidity('');
        }
      }

      // Custom rule: Expected Close Date cannot be in the past for active opportunities
      const closeDateInput = form.querySelector('input[name="expected_close_date"]');
      const stageSelect = form.querySelector('select[name="stage"]');
      if (closeDateInput && closeDateInput.value) {
        const todayStr = new Date().toISOString().split('T')[0];
        const isClosed = stageSelect && (stageSelect.value === 'Won' || stageSelect.value === 'Lost');
        if (!isClosed && closeDateInput.value < todayStr) {
          closeDateInput.setCustomValidity('Expected Close Date cannot be in the past.');
          isValid = false;
        } else {
          closeDateInput.setCustomValidity('');
        }
      }

      // Custom rule: Follow-up Date cannot be in the past for new planned follow-up
      const followDateInput = form.querySelector('input[name="follow_up_date"], input[name="new_date"]');
      const statusSelect = form.querySelector('select[name="status"]');
      if (followDateInput && followDateInput.value) {
        const todayStr = new Date().toISOString().split('T')[0];
        const isPlanned = !statusSelect || statusSelect.value === 'Planned';
        if (isPlanned && followDateInput.value < todayStr) {
          followDateInput.setCustomValidity('Follow-up date cannot be earlier than today.');
          isValid = false;
        } else {
          followDateInput.setCustomValidity('');
        }
      }

      // Standard HTML5 validation check
      if (!form.checkValidity() || !isValid) {
        event.preventDefault();
        event.stopPropagation();
      }

      form.classList.add('was-validated');
    }, false);
  });

  // 4. Lead Conversion toggle logic
  const createOppCheckbox = document.getElementById('create_opp_checkbox');
  const oppFieldsContainer = document.getElementById('opp_fields_container');
  if (createOppCheckbox && oppFieldsContainer) {
    function toggleOppFields() {
      if (createOppCheckbox.checked) {
        oppFieldsContainer.style.display = 'block';
      } else {
        oppFieldsContainer.style.display = 'none';
      }
    }
    createOppCheckbox.addEventListener('change', toggleOppFields);
    toggleOppFields();
  }
});
