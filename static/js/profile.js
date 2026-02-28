document.addEventListener('DOMContentLoaded', function () {

  const toggleBtn = document.getElementById('edit-toggle');
  const editPanel = document.getElementById('edit-panel');
  const cancelBtn = document.getElementById('edit-cancel');

  function openEdit(){
      editPanel.setAttribute('aria-hidden','false');
      toggleBtn.textContent="Close";
  }

  function closeEdit(){
      editPanel.setAttribute('aria-hidden','true');
      toggleBtn.textContent="Edit Profile";
  }

  toggleBtn.addEventListener('click',function(){
      const open = editPanel.getAttribute('aria-hidden') === 'false';
      open ? closeEdit() : openEdit();
  });

  if(cancelBtn){
      cancelBtn.addEventListener('click',closeEdit);
  }

});