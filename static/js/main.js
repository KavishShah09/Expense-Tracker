$(document).ready(function () {
	$('.delete-transaction').click(function () {
		var id = $(this).attr('data-id');
		var url = $(this).attr('data-url');

		$('.modal-form', 'input').val(id);
		$('.modal-form').attr('action', url);
	});
});
