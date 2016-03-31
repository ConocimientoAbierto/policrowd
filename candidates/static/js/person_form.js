/* Get the element that should have its visibility changed to hide or show
   a Select2. */

function getSelect2Enclosure(selectElement) {
  /* This assumes that there's a label that's a sibling of the
   * Select2, and that they're the only elements in a containing
   * element (the one that will be returned by this function) */
  return selectElement.select2('container').parent();
}

/* Change the visibility of a Select2 widget; select2Element should be a
   jQuery-wrapped element */

function setSelect2Visibility(select2Element, visibility) {
  /* If visibility is false, this both disables the Select2 boxes and
   * hides them by hiding their enclosing element. Otherwise it
   * enables it and makes the enclosure visible. */
  var enclosure = getSelect2Enclosure(select2Element);
  select2Element.prop(
    'disabled',
    !visibility
  );
  if (visibility) {
    enclosure.show()
  } else {
    enclosure.hide();
  }
}

/* Make all the party drop-downs into Select2 widgets */

function setUpPartySelect2s() {
  $('.party-select').select2({width: '100%'});
}

/* Make all the post drop-downs into Select2 widgets */

function setUpPostSelect2s() {
  $('.post-select').each(function(i) {
    var postSelect = $(this),
      hidden = postSelect.prop('tagName') == 'INPUT' &&
         postSelect.attr('type') == 'hidden';
    /* If it's a real select box (not a hidden input) make it into a
     * Select2 box */
    if (!hidden) {
      postSelect.select2({
        placeholder: 'Post',
        allowClear: true,
        width: '100%'
      });
    }
    postSelect.on('change', function (e) {
      updateFields();
    });
    updateFields();
  });
}

/* Set the visibility of an input element and any label for it */

function setVisibility(plainInputElement, newVisiblity) {
  var inputElement = $(plainInputElement),
      inputElementID = plainInputElement.id,
      labelElement = $('label[for=' + inputElementID + ']');
  inputElement.toggle(newVisiblity);
  labelElement.toggle(newVisiblity);
}


/* Update the visibility of the party and post drop-downs for a particular
   election */

function updateSelectsForElection(show, election) {
  /* Whether we should show the party and post selects is
     determined by the boolean 'show'. */
  var partySelectToShowID,
      partyPositionToShowID,
      postID = $('#id_constituency_' + election).val(),
      partySet;
  if (postID) {
    partySet = postIDToPartySet[postID];
  }
  if (show) {
    if (postID) {
      partySelectToShowID = 'id_party_' + partySet + '_' + election;
      partyPositionToShowID = 'id_party_list_position_' + partySet + '_' + election;
      $('.party-select-' + election).each(function(i) {
        setSelect2Visibility(
          $(this),
          $(this).attr('id') == partySelectToShowID
        );
      });
      $('.party-position-' + election).each(function(i) {
        setVisibility(this, $(this).attr('id') == partyPositionToShowID);
      });
    } else {
      /* Then just show the first party select and hide the others: */
      $('.party-select-' + election).each(function(i) {
        setSelect2Visibility($(this), i == 0);
      });
      $('.party-position-' + election).each(function(i) {
        setVisibility(this, i == 0);
      });
    }
  } else {
    $('.party-select-' + election).each(function(i) {
      setSelect2Visibility($(this), false);
    });
    $('.party-position-' + election).each(function() {
      setVisibility(this, false);
    });
  }
  setSelect2Visibility($('#id_constituency_' + election), show);
}

/* Make sure that the party and constituency select boxes are updated
   when you choose whether the candidate is standing in that election
   or not. */

function setUpStandingCheckbox() {
  $('#person-details select.standing-select').on('change', function() {
    updateFields();
  });
}

/* This should be called whenever the select drop-downs for party
   and post that have to be shown might have to be shown.  */

function updateFields() {
  $('#person-details select.standing-select').each(function(i) {
    var standing = $(this).val() == 'standing',
        match = /^id_standing_(.*)/.exec($(this).attr('id')),
        election = match[1];
    updateSelectsForElection(standing, election); });
}

/*
  Set the change() events for the Area selects.
*/

function fillAreasCombo(id, areas){
  $(id).find('option').remove();
  $(id).append($("<option></option>").attr("value", -1).text(" ")); 
  $.each(areas, function(name, data) {
    $(id)
      .append(
        $("<option></option>")
        .attr("value", data.id)
        .text(name)
      ); 
  });
}

function clearPostsView(){
  $('#id_first_areas').val(-1);
  $('#id_second_areas').find('option').remove();
  $('#id_posts').find('option').remove();
  $('#id_other_post').val('');
}

function fillPostsCombo(id, posts){
  $(id).find('option').remove();
  $(id).append($("<option></option>").attr("value", -1).text(" ")); 
  posts.forEach(function(post){
    $(id)
      .append(
        $("<option></option>")
        .attr("value", post.id)
        .text(post.role)
      ); 
  });
}

function setPostsEvents(areasTree) {
  var firstAreasComboId = '#id_first_areas';
  fillAreasCombo(firstAreasComboId, areasTree);
  $(firstAreasComboId).val(-1);

  $('#add_post_btn').click(function(){
    clearPostsView();
    $('#post_view').slideDown();
    $(this).slideUp();
  });

  $('#hide_post_btn').click(function(){
    $('#post_view').slideUp();
    clearPostsView();
    $('#add_post_btn').slideDown();
  });

  $(firstAreasComboId).change(function(eventData){
    var parentName = $(this).find("option:selected").text();
    var parentId = $(this).find("option:selected").val();
    if (parentId != -1){
      var internalAreas = window.areasTree[parentName]['internal_areas'];
      
      var secondAreasComboId = '#id_second_areas';
      fillAreasCombo(secondAreasComboId, internalAreas);
      $(secondAreasComboId).val(-1);
      $('.second_areas').slideDown();

      var postsComboId = '#id_posts';
      fillPostsCombo(postsComboId, window.posts[parentId]);
      $(postsComboId).val(-1);
      $('.posts').slideDown();
    } else {
      $('.second_areas').slideUp();
      $('.posts').slideUp();
    }
  });
}

$(document).ready(function() {
  $.getJSON('/post-id-to-party-set.json', function(data) {
    window.postIDToPartySet = data;
    setUpPartySelect2s();
    setUpPostSelect2s();
    setUpStandingCheckbox();
    updateFields();
  });

  $.getJSON('/areas-tree.json', function(areasTree) {
    $.getJSON('/posts-by-area.json', function(postsByArea){
      window.posts = postsByArea;
    });
    window.areasTree = areasTree;
    setPostsEvents(areasTree);
  });

  

});
