$(function(){
	// checkbox select all or cancel all
	$("input[name='checkall']").click(function(){
		var checkbox = $("input[name='cc']");
		if(this.checked){
			checkbox.prop("checked", true);  
		}else{
			checkbox.prop("checked", false);
		}
	});

	$("input[name='confirm_task']").click(function(){
		var result = gether_table();
		$("#hidTD").val(JSON.stringify(result));
		$("#form").submit();
	});

	$("input[name='submit_checkbox']").click(function(){
		var result = gether_checkbox();
		$("#hidTD").val(JSON.stringify(result));
		$("#form").submit();
	});

})

// function update_waitlist(){
	  // record all checkbox val
		// var all = [];
		// $("input:checkbox").each(function() {
		// 		all.push($(this).attr("value"));
		// });

		// addup checked values
// 		var che = [];
// 		$("input[name='cc']:checked").each(function() {
// 				che.push({"11":$(this).val()});
// 		});
// 		alert(che)
// 		// post result
// 		$.post("/dashboard/waitlist",{wailist:che});

// 		//remove checked
// 		$("input:checkbox").each(function() {
// 			$(this).prop("checked", false);
// 		});
// 		alert("added to waitlist");
// }

function remove_from_waitlist(obj){
	var tr = obj.parentNode.parentNode;
	var tds = $(tr).find("td");
	$.post("/dashboard/waitlist", {delete:$(tds[0]).html()});
	tr.parentNode.removeChild(tr);
}
function process_task(obj){
	alert(obj.href)
	var tr = obj.parentNode.parentNode;
	var tds = $(tr).find("td");
	$.post("/deploy/list/work", {"method":obj.name,"id":$(tds[0]).html()});
}
function trasfer_data(obj){
	var tr = obj.parentNode.parentNode;
	var tds = $(tr).find("td");
	$.get("/deploy/assignment", {"stgs":$(tds[4]).html()});
}
function withdraw(obj){
		var tr = obj.parentNode.parentNode;
		var tds = $(tr).find("td");
		document.getElementById(obj.name).innerHTML="withdrawn";
		document.getElementById("link"+obj.name).innerHTML="N/A";
		$.get("/dashboard/task_sheet/"+obj.name);
    }

	
function gether_table(){
	var tr = $("#table tr");
	var result = [];
	
	for (var i=1; i<tr.length; i++){
		var tds = $(tr[i]).find("td");
		if (tds.length>0){
			result.push($(tds[1]).html());
		}
	}
	return result
}

function gether_checkbox(){
	var result = [];
	$("input[name='cc']").each(function(){
		if(this.checked){
			var row = $(this).parent("td").parent("tr");//获取当前行
			var tds = $(row).find("td");
			result.push({"name":$(tds[1]).html(), "id":$(this).val()});
		}
		
	})
	return result
}