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
    
    $(".navbar-nav").find("li").each(function () {
        var a = $(this).find("a:first")[0];
        if ($(a).attr("href") === location.pathname) {
            $(this).addClass("active");
        } else {
            $(this).removeClass("active");
        }
    });
})
function GoBackward(){
    window.history.back();
    }

function remove_row(obj){
	var tr = obj.parentNode.parentNode;
    var tds = $(tr).find("td");
	$.post("/ding?delete="+obj.name);
	tr.parentNode.removeChild(tr);
}
function process_task(obj){
	var tr = obj.parentNode.parentNode;
    var tds = $(tr).find("td");
    var _id = $(tds[0]).html();
    document.getElementById(_id).innerHTML = obj.name;
	document.getElementById("link"+_id).innerHTML="N/A";
	$.post("/deploy/list/work", {"method":obj.name,"id":_id});
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
			result.push({"name":$(this).val(),"id":$(tds[2]).html()});
		}
		
	})
	return result
}
function check_name(){
    var originName = $.trim($("input[name='name']").val());
    if(originName){
        $.ajax({
            url:"/dy",
            type: "GET",
            dataType:"json",
            data: {"checkName":originName},
            success:check_name_success
        });
    }
    else{
        $("#nametip").html('');
    }
}
function check_ding(){
    var originName = $.trim($("input[name='ding_name']").val());
    if(originName){
        $.ajax({
            url:"/dy",
            type: "GET",
            dataType:"json",
            data: {"checkDing":originName},
            success:check_name_success
        });
    }
    else{
        $("#nametip").html('名称必填');
    }
}

function check_user(){
    var originName = $.trim($("input[name='name']").val());
    if(originName){
        $.ajax({
            url:"/dy",
            type: "GET",
            dataType:"json",
            data: {"checkUser":originName},
            success:check_name_success
        });
    }
    else{
        $("#nametip").html('');
    }
}
function check_name_success(response){
    if(response){
        $("input[name='name']").css({"color":'red'});
        document.getElementById("nametip").className ="prompt_alert";
        $("#nametip").html('该用户名已经被使用');
    }else{
        $("input[name='name']").css({"color":'green'});
        document.getElementById("nametip").className ="prompt";
        $("#nametip").html('该用户名可用');
    }
}
function getAccount(_id) {
    $.ajax({
        url:"/dy",
        type: "GET",
        dataType:"json",
        data: {"getAccount":"accounts"},
        success:function(response){
            if(response){
                var parent = document.getElementById(_id);
                clearOption(parent);
                var opt=document.createElement("option");
                opt.text = " choose exchage";
                opt.value = " ";
                parent.options.add(opt);
                var res = Object.keys(response);
                addOption(parent, res);
            }else{
                $("#actip").html('账户连接失败');
            }
        },
    });
}
function updateAccount(obj){
    var _id = obj.parentNode.firstElementChild.id;
    getAccount(_id);
}
function changeOpt(obj){
    $.ajax({
        url:"/dy",
        type: "GET",
        dataType:"json",
        data: {"getAccount":"accounts"},
        success:function(response){
            if(response){
                var _id = obj.parentNode.id;
                var p_value = obj.value;
                var child = document.getElementById("child"+_id);
                clearOption(child);
                addOption(child,response[p_value][0]);

                var child2 = document.getElementById("child2"+_id);
                clearOption(child2);
                addOption(child2,response[p_value][1]);
            }else{
                $("#actip").html('账户连接失败');
            }
        },
    });
}

function clearOption(obj){
    var c_length = obj.options.length;
    if(c_length>0){
        for(var i=0;i<c_length;i++){
            obj.options.remove(0);
        }
    }
}

function addOption(obj, content){
    for (_id in content){
        var opt=document.createElement("option");
        opt.text = content[_id];
        opt.value = content[_id];
        obj.options.add(opt);
    }
}

function addSymbolRow(obj){
    var add_item = obj.parentNode;
    var nodeFather = obj.parentNode.parentNode;
    var node_clone = add_item.cloneNode(true); 
    node_clone.id = add_item.id+1
    node_clone.children[0].id = add_item.children[0].id+1;
    node_clone.children[1].id = add_item.children[1].id+1;
    node_clone.children[2].id = add_item.children[2].id+1;
    nodeFather.appendChild(node_clone); 
    getAccount(node_clone.children[0].id);
}

function removeSymbolRow(obj){
    var add_item = obj.parentNode;
    var nodeFather = obj.parentNode.parentNode;
    nodeFather.removeChild(add_item); 
}

function loading_response(){
    //获取浏览器页面可见高度和宽度
    var _PageHeight = document.documentElement.clientHeight,
        _PageWidth = document.documentElement.clientWidth;
    //计算loading框距离顶部和左部的距离（loading框的宽度为215px，高度为61px）
    var _LoadingTop = _PageHeight > 61 ? (_PageHeight - 61) / 2 : 0,
        _LoadingLeft = _PageWidth > 215 ? (_PageWidth - 215) / 2 : 0;
    //在页面未加载完毕之前显示的loading Html自定义内容
    var _LoadingHtml = '<div id="loadingDiv" style="position:absolute;left:0;width:100%;height:' + _PageHeight + 'px;top:0;background:#f3f8ff;opacity:1;filter:alpha(opacity=80);z-index:10000;"><div style="position: absolute; cursor1: wait; left: ' + _LoadingLeft + 'px; top:' + _LoadingTop + 'px; width: auto; height: 57px; line-height: 57px; padding-left: 50px; padding-right: 5px; background: #fff url({{static_url("loadding.gif")}} no-repeat scroll 5px 10px; border: 2px solid #95B8E7; color: #696969; font-family:\'Microsoft YaHei\';">策略部署中，请等待...</div></div>';
    //呈现loading效果
    document.write(_LoadingHtml);

    //window.onload = function () {
    //    var loadingMask = document.getElementById('loadingDiv');
    //    loadingMask.parentNode.removeChild(loadingMask);
    //};

    //监听加载状态改变
    document.onreadystatechange = completeLoading;

    //加载状态为complete时移除loading效果
    function completeLoading() {
        if (document.readyState == "complete") {
            var loadingMask = document.getElementById('loadingDiv');
            loadingMask.parentNode.removeChild(loadingMask);
        }
    }
}

function operator(obj) {
    var s = obj.name.split("-");
    var name = s[1];
    var method = s[0];
    var tr = obj.parentNode.parentNode;
	var tds = $(tr).find("td");

    $.ajax({
        url:"/operator",
        type: "POST",
        dataType:"json",
        data: {"name":name,"method":method},
        beforeSend:task_processing(obj),
        error:restore_button(obj),
        success:function(response){
            if(response){
                if (method=="halt"){$(tds[2]).html("idle");};
            }else{
                restore_button(obj);
                alert(name+" "+method+" operation failed");
            }
        },
    });
}
function task_processing(obj){
    $(obj).attr("disabled","disabled");
    $(obj).css("pointer-events","none");
}
function restore_button(obj){
    $(obj).attr("disabled",false);
    $(obj).css("pointer-events","auto");
}

function render(instrument,pnl){
    Highcharts.chart(instrument, {
       chart: {
             zoomType: 'x'
       },
       title: {
             text: 'PnL Chart Over Time'
       },
       subtitle: {
             text: document.ontouchstart === undefined ?
                'Click and drag in the plot area to zoom in' : 'Pinch the chart to zoom in'
       },
       xAxis: {
             type: 'datetime'
       },
       yAxis: {
             title: {
                text: 'PnL'
             }
       },
       legend: {
             enabled: false
       },
       plotOptions: {
             area: {
                fillColor: {
                   linearGradient: {
                         x1: 0,
                         y1: 0,
                         x2: 0,
                         y2: 1
                   },
                   stops: [
                         [0, Highcharts.getOptions().colors[0]],
                         [1, Highcharts.Color(Highcharts.getOptions().colors[0]).setOpacity(0).get('rgba')]
                   ]
                },
                marker: {
                   radius: 2
                },
                lineWidth: 1,
                states: {
                   hover: {
                         lineWidth: 1
                   }
                },
                threshold: null
             }
       },
 
       series: [{
             type: 'line',
             name: 'pnl',
             data: pnl
       }]
    })
 };
 
//查找表格的<th>元素，让它们可单击
function makeSortable(table) {
    var headers=table.getElementsByTagName("th");
    for(var i=0;i<headers.length;i++){
        (function(n){
            var flag=false;
            headers[n].onclick=function(){
                // sortrows(table,n);
                var tbody=table.tBodies[0];//第一个<tbody>
                var rows=tbody.getElementsByTagName("tr");//tbody中的所有行
                rows=Array.prototype.slice.call(rows,0);//真实数组中的快照

                //基于第n个<td>元素的值对行排序
                rows.sort(function(row1,row2){
                    var cell1=row1.getElementsByTagName("td")[n];//获得第n个单元格
                    var cell2=row2.getElementsByTagName("td")[n];
                    var val1=cell1.textContent||cell1.innerText;//获得文本内容
                    var val2=cell2.textContent||cell2.innerText;

                    if(val1<val2){
                        return -1;
                    }else if(val1>val2){
                        return 1;
                    }else{
                        return 0;
                    }
                });
                if(flag){
                    rows.reverse();
                }
                //在tbody中按它们的顺序把行添加到最后
                //这将自动把它们从当前位置移走，故没必要预先删除它们
                //如果<tbody>还包含了除了<tr>的任何其他元素，这些节点将会悬浮到顶部位置
                for(var i=0;i<rows.length;i++){
                    tbody.appendChild(rows[i]);
                }

                flag=!flag;
            }
        }(i));
    }
}

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
//        var link=location.href.substring(location.href.indexOf("?")+1);
//       var ding_name = link.split("=")[1];
//        $.post("/ding?delete="+ding_name);
// }