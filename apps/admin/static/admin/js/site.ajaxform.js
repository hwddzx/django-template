//
//返回一个input的元素对应的Label的显示名字。
//
//比如下面的表单项:
//<label for="id_name">应用名称</label>
//<input class="required valid" id="id_name" maxlength="64" name="name" placeholder="应用名称，必填项" type="text">
//
//getInputLabelText($form, 'name') 返回 '应用名称'
//
function getInputLabelText($form, inputName) {
  var $label = $('label[for="id_'+inputName+'"]', $form);
  if ($label) {
    return $label.text();
  }

  // 如果找不到，尝试在不加再试一次
  $label = $('label[for="'+inputName+'"]', $form);
  if ($label) {
    return $label.text();
  }

  return inputName;
}

//
//格式化错误消息。
//
//response - JSON请求的响应
//
//只有 response['ret'] != 0 的时候才表示错误。
//
function formatResponseErrorMessage($form, response) {
  // e.g.
  // "ret": 1004
  if (response['ret'] === 0) {
    return null;
  }

  var errmsg = '';

  // e.g.
  // "errmsg-detail": {"id": ["系统不存在输入的应用ID"]}
  var errmsgDetail = response['errmsg-detail'];   // 包含各个字段的错误的更详细信息
  if (errmsgDetail) {
     errmsg += "<ul>";
     for (var fieldName in errmsgDetail) {
       errmsg += "<li>";
       errmsg += "<strong>" + getInputLabelText($form, fieldName) + "</strong>";
       errmsg += ": ";
       errmsg += errmsgDetail[fieldName];
       errmsg += "</li>";
     }
     errmsg += "</ul>";
  } else {
     // 如果没有详细的错误信息，使用errmsg字段来显示错误
     // e.g.
     // "errmsg": "验证表单失败，请确认表单的必填项都填写完整和数据格式正确"
     errmsg = response['errmsg'];
     if (response['detail']) {
         errmsg += "<h4>详细信息</h4>" + response['detail'];
     }
  }
  return errmsg;
}

// 表单提交错误时调用
function showFormSubmitError($form, errmsg) {
  var $alert = $('#id_form_alert', $form);
  console.log($alert);
  $alert.addClass('alert-warning').removeClass('alert-success');
  $alert.html('<h4>错误信息</h4> ' + errmsg);
  $alert.removeClass("hidden");
}

//
//当表单返回错误时候调用这个函数来显示错误信息
//e.g.
//
// $form.ajaxForm({
//     dataType:  'json',
//     success:   function(response) {
//           if (response['ret'] == 0) {
//               showFormSubmitSuccess($form, '修改成功');
//           } else {
//               showFormErrorResponse($form, response);
//           }
//     }
// });
//
function showFormErrorResponse($form, response) {
  var errmsg = formatResponseErrorMessage($form, response);
  if (errmsg) {
    showFormSubmitError($form, errmsg);
  }
}

// 表单提交成功是调用
function showFormSubmitSuccess($form, msg, afterShowMessageCallback) {
  var $alert = $('#id_form_alert', $form);
  $alert.html('<h4>成功</h4> ' + msg);
  $alert.addClass('alert-success').removeClass('alert-warning');
  $alert.removeClass("hidden");
  if (afterShowMessageCallback){
    afterShowMessageCallback();
  }
}

// 隐藏表单的提交信息，当表单内容改变时会自动调用
function hideFormSubmitMessage($form) {
  var $alert = $('#id_form_alert', $form);
  $alert.addClass("hidden");
}

// 文本输入框长度限制提示
function input_limit_func() {
  var limit = parseInt($(this).attr('maxlength')) || parseInt($(this).attr('data-maxlength')) || 100;
  $(this).inputlimiter({
    "limit": limit,
    remText: '还可以输入%n字, ',
    limitText: '最多可以输入 : %n.'
  });
}

function confirmMessage(message, options){
  bootbox.dialog({
    message: '<h3 class="header smaller lighter red">信息</h3><div class="alert alert-warning">' +
        '<h4><i class="ace-icon bigger-200 fa fa-question-circle"></i>&nbsp;'+message+'</h4></div>',
    buttons: {
      main: {
        label: "取消",
        className: "btn-primary",
        callback: options.cancelCallback ? options.cancelCallback : null
      },
      danger: {
        label: "确定",
        className: "btn-danger",
        callback: options.actionCallback ? options.actionCallback : null
      }
    }
  }).find("div.modal-dialog").removeClass("modal-dialog");
}

function alertError(message){
  bootbox.dialog({
    message: '<h3 class="header smaller lighter red">错误</h3><div class="alert alert-danger"> ' +
        '<i class="ace-icon bigger-200 fa fa-exclamation-triangle"></i>&nbsp;'+message+'</div>',
    buttons: {
      danger: {
        label: "确定",
        className: "btn-danger"
      }
    }
  }).find("div.modal-dialog").removeClass("modal-dialog");
}

function showMessage(message){
  bootbox.dialog({
    message: '<h3 class="header smaller lighter red">信息</h3><div class="alert alert-block alert-success"> ' +
        '<i class="ace-icon bigger-200 fa fa-check-"></i>&nbsp;'+message+'</div>',
    buttons: {
      danger: {
        label: "确定",
        className: "btn-primary"
      }
    }
  }).find("div.modal-dialog").removeClass("modal-dialog");
}

// show an animated progressbar for the form based on modal
function startProgressBar() {
  $('#id-progress-bar-container').show();
  var $progressbar = $( "#id-progress-bar" );
  var refreshIntervalId = window.setInterval(function() {
    // use the parent container width as max width
    var maxWidth = $('#id-progress-bar-container').width();
    // generate a random number between the max and it's half,
    // make the bar move back and forth before we get the callback event
    var randomProgress = Math.floor(Math.random() * (maxWidth - maxWidth/2 + 1) + maxWidth/2);
    // reset when max reached
    var step = randomProgress >= maxWidth ? maxWidth: randomProgress;
    $progressbar.width(step);
  },1000);
  return refreshIntervalId;
}

// stop the progressbar for the form based on modal
function stopProgressBar(refreshIntervalId) {
  $('#id-progress-bar-container').hide();
  $('#id-progress-bar').width(0);
  window.clearInterval(refreshIntervalId);
}

//使用bootbox显示简单的提示信息
function bootboxAlert(title, msg) {
  bootbox.dialog({
    message: "<div class='alert alert-block alert-warning'>" + msg + "</div>",
    title: title,
    buttons: {
      success: {
        label: "关闭",
        className: "btn-success"
      }
    }
  }).find("div.modal-dialog").removeClass("modal-dialog");
}

function bootboxConfirm(message, options){
  bootbox.dialog({
    message: '<h3 class="header smaller lighter red">信息</h3><div class="alert alert-warning">' +
        '<h4><i class="ace-icon bigger-200 fa fa-question-circle"></i>&nbsp;' + message + '</h4></div>',
    buttons: {
      main: {
        label: "取消",
        className: "btn-primary",
        callback: options.cancelCallback ? options.cancelCallback : null
      },
      danger: {
        label: "确定",
        className: "btn-danger",
        callback: options.actionCallback ? options.actionCallback : null
      }
    }
  }).find("div.modal-dialog").removeClass("modal-dialog");
}

function showServerError(error){
  var msg = error['errmsg-detail']['__all__'];
  if (!msg) {
    msg = "";
    $.each(error["errmsg-detail"], function(key, value){
      msg += value + "<br>";
    });
  }
  bootboxAlert("保存出错", "错误信息:<b><h3><strong>" + msg + "</strong></h3>");
}

(function($){

  $.fn.enableAceFileInput = function (extendName) {
    this.ace_file_input({
      style: 'well',
      thumbnail: 'large',
      no_file: '无 ...',
      btn_choose: '选择文件(' + extendName + ')',
      btn_change: '修改',
      before_change: function (files, dropped) {
        var file = files[0];
        var file_name;
        if (typeof file == "string") {
          file_name = file;
        } else {
          file_name = file.name;
          if (file.size == 0) {
            file_name = "";
          }
        }
        var filter = new RegExp("\\.(" + extendName + ")$", "i");
        //file is just a file name here (in browsers that don't support FileReader API such as IE8)
        var is_valid = filter.test(file_name);
        if (!is_valid) {
          bootboxAlert('出错了', '请选择正确类型的文件!');
        }
        return is_valid;
      }
    });
  };

  $.fn.enableAceImageInput = function (maxWidth, maxHeight, minWidth, minHeight) {
    var extendName = "jpg|bmp|png|jpeg|gif";
    var ace_file_input = this.ace_file_input({
      style: 'well',
      thumbnail: 'large',
      no_file: '无 ...',
      btn_choose: '选择图片(' + extendName + ')',
      btn_change: '修改',
      before_change: function (files, dropped) {
        var file = files[0];
        var file_name;
        if (typeof file == "string") {
          file_name = file;
        } else {
          file_name = file.name;
          if (file.size == 0) {
            file_name = "";
          }
        }
        var filter = new RegExp("\\.(" + extendName + ")$", "i");
        //file is just a file name here (in browsers that don't support FileReader API such as IE8)
        var is_picture = filter.test(file_name);
        if (is_picture) {
          // check image size to avoid to exceed the max width and height
          var img = new Image();
          img.onload = function() {
            if ((maxWidth && this.width > maxWidth) || (maxHeight && this.height > maxHeight)) {
              bootbox.dialog('图片' + file_name +'尺寸 ' + this.width + 'x' + this.height + '超过了最大允许尺寸 ' + maxWidth + 'x' + maxHeight,
                  [{"label": "确定"}]);
              ace_file_input.data('ace_file_input').reset_input();
            }
            if ((minWidth && this.width < minWidth) || (minHeight && this.height < minHeight)) {
              bootbox.dialog('图片' + file_name +'尺寸 ' + this.width + 'x' + this.height + '不满足最小尺寸 ' + minWidth + 'x' + minHeight,
                  [{"label": "确定"}]);
              ace_file_input.data('ace_file_input').reset_input();
            }
          };
          var _URL = window.URL || window.webkitURL;
          img.src = _URL.createObjectURL(file);
        } else {
          bootboxAlert('出错了', '请选择正确的图片!');
        }
        return is_picture;
      }
    });
  };

  $.fn.buildFormValidationRules = function (shouldFillPlaceholder) {
    var rules = {};
    var $form = this;
    shouldFillPlaceholder = shouldFillPlaceholder || false;
    $("input, textarea", $form).each(function () {
      var name = $(this).attr('name');
      var rule = {};

      if ($(this).hasClass("required")) {
        rule['required'] = true;
        // set the placeholder if has no value
        if (shouldFillPlaceholder && !$(this).attr('placeholder')) {
          var label = getInputLabelText($form, name);
          if (label) {
            $(this).attr('placeholder', $.trim(label) + " 必填");
          }
        }
      }
      if ($(this).attr('maxlength')) {
        rule['rangelength'] = [ 1, parseInt($(this).attr('maxlength'))];
        $(this).data().maxlength = $(this).attr('maxlength');
      }
      if ($(this).data('regex')) {
        rule['regex'] = $(this).data('regex');
      }
      if (Object.keys(rule).length > 0) {
        rules[name] = rule
      }
    });
    return rules;
  };

  $.fn.showServerResponseError = function (responseText, req, targetUrl) {
    var errmsg = '出错啦。';

    if (req.status) {
      errmsg = errmsg + '服务器状态码: ' + req.status + '。';
    }
    if (targetUrl) {
      errmsg += '目标页面: ' + targetUrl;
    }
    errmsg += '<pre>' + responseText + "</pre>";
    this.html('<div class="well well-large well-transparent lead">\
                  <i class="fa fa-warning-sign fa-2x pull-left"></i> ' + errmsg + '</div>');
  };

  $.fn.buildAjaxFormOptions = function(options){
    var $form = this;
    var refreshIntervalId;
    options = options || {};
    if (this.data("modal_show") && !options.successCallback) {
      $.extend(options, {successCallback: function(response) {
        $form.closest(".modal").modal('toggle');
        // should broadcast the page dirty to tell listener to refresh page.
        $.event.trigger({type: "onPageDirty"});
      }});
    }
    return {
      dataType: 'json',
      data: options.data,
      beforeSubmit: function (formData, jqForm) {
        var is_valid = $form.valid();
        if (is_valid && options.beforeSubmit) {
          is_valid =  options.beforeSubmit(formData, jqForm);
        }
        if (is_valid) {
          refreshIntervalId = startProgressBar();
        }
        $(":submit", $form).attr("disabled", is_valid);
        return is_valid
      },
      beforeSerialize: function(form, formOptions) {
        if (options.beforeSerialize) {
          options.beforeSerialize(form, formOptions);
        }
      },
      // success identifies the function to invoke when the server response
      // has been received
      success: function (response) {
        stopProgressBar(refreshIntervalId);
        if (response['ret'] == 0) {
          if (options.successCallback) {
            options.successCallback(response);
          } else {
            var message = response['msg'] || '保存成功!';
            showFormSubmitSuccess($form, message, function () {
              if (options.shouldNotBack) {
              } else {
                window.history.go(-1);
              }
            });
          }
        } else {
          if (options.failCallback) {
            options.failCallback(response);
          } else {
            var commonMsg = response['errmsg-detail']['__all__'];
            if (commonMsg) {
              showFormSubmitError($form, commonMsg);
              delete response['errmsg-detail']['__all__'];
            }
            var validator = $form.validate();
            validator.showErrors(response['errmsg-detail']);
          }
        }
        $(":submit", $form).attr("disabled", false);
      },

      error: function (xhr, textStatus, errorThrown) {
        stopProgressBar(refreshIntervalId);
        $form.showServerResponseError(xhr.responseText, xhr, $form.attr('action'));
        $(":submit", $form).attr("disabled", false);
      }
    };
  };

  $.fn.enableChosen = function (options) {
    var controls = $(this);

    $(this).attr("data-placeholder", "请选择...");
    controls.each(function(){
      // XXX: chosen doesn't calculate width of control well in case of hidden if control doesn't specify width
      // so check the data-width and apply it to control if need to avoid above issue.
      var width = $(this).data("width");
      var defaultOptions = {no_results_text: '没有找到数据',
                            default_multiple_text: '可选择多项',
                            search_contains: true,
                            disable_search_threshold: 20
      };
      if (width) {
        defaultOptions['width'] = width;
      }
      return $(this).chosen($.extend(defaultOptions, options || {}));
    });
  };

  $.fn.enablePopoverForCrispyForm = function() {
    // crispy form render the help text as <p id=""hint_xxxx" class="help-box"> help </p>
    // so convert it to bootstrap popover
    var controls = $(this);
    controls.each(function () {
      // remove prepended key "hint_"
      var $popover = $('<i class="fa fa-question-circle" style="padding-left:5px;"></i>');
      $("label[for='" + this.id.substring(5) + "']").append($popover);
      $popover.popover({
        'placement': 'right',
        'trigger': 'hover',
        'content': $(this).text(),
        'title': '提示',
        'container': "form"
      });

      $(this).remove();
    });
  };

  $.fn.enableDatePicker = function(options) {
    var date_picker_options = { format: "yyyy-mm-dd", language: "zh-CN", weekStart: 1, maxDate: "+0D" };
    $.extend(date_picker_options, options || {});
    // remove "class" flag to make the change effected.
    $(this).removeClass("hasDatepicker").datepicker(date_picker_options);
  };

  //由于html的限制, 如果field的属性disabled为true, form表单不会提交该field的数据到服务器
  //在这种情况下, 需要手动打包disabled数据上传.
  $.fn.serializeDisabled = function () {
    var obj = [];
    $(':disabled[name]', this).each(function () {
      obj.push({name: this.name, value: $(this).val()});
    });
    return obj;
  };

})(jQuery);
