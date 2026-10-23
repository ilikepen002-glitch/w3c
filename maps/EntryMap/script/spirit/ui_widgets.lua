-- Thin Y3 UI construction helpers. The editor supplies one verified root canvas.
local W={}
-- Verified in the running editor: 100547 is an opaque white rectangle;
-- 131155 is a translucent decorative button and cannot serve as a panel fill.
local solid_image=100547
W.colors={panel='#101f31',deep='#08121e',button='#263f52',accent='#e7ba66',text='#e5edf3',muted='#8ea9b9',teal='#59d2c3',danger='#e58d89'}
local function place(ui,x,y,w,h)
    ui:set_anchor(0,0);ui:set_pos(x,y);ui:set_ui_size(w,h)
    return ui
end
local function image_color(ui,color,alpha)
    -- HEX avoids ambiguous RGB component units across editor versions.
    ui:set_image_color_hex(color,alpha)
end
function W.container(parent,w,h)
    local ui=place(parent:create_child('空节点'),0,0,w,h)
    ui:set_intercepts_operations(false)
    return ui
end
function W.fit_viewport(width,height)
    if type(width)~='number' or type(height)~='number' or width~=width or height~=height
        or width<=0 or height<=0 or width==math.huge or height==math.huge then return nil end
    local scale=math.min(width/1920,height/1080)
    return scale,(width-1920*scale)/2,(height-1080*scale)/2
end
function W.panel(parent,x,y,w,h,color)
    local ui=place(parent:create_child('图片'),x,y,w,h)
    ui:set_image(solid_image)
    image_color(ui,color or W.colors.panel,100)
    ui:set_intercepts_operations(true)
    return ui
end
function W.label(parent,x,y,w,h,text,size,color)
    local ui=place(parent:create_child('文本'),x,y,w,h)
    ui:set_font_size(size or 18);ui:set_text_color_hex(color or W.colors.text,100)
    ui:set_text_alignment('左','上');ui:set_text(text or '');ui:set_intercepts_operations(false)
    return ui
end
function W.button(parent,x,y,w,h,text,callback,primary)
    local ui=place(parent:create_child('按钮'),x,y,w,h)
    -- Native button skins ignore the image tint API in the running editor.
    -- Keep all four states transparent; a non-intercepting image provides color.
    for status=1,4 do
        ui:set_btn_status_image(status,999)
        ui:set_btn_status_string(status,'')
    end
    local background=place(ui:create_child('图片'),0,0,w,h)
    background:set_image(solid_image)
    image_color(background,primary and '#25645f' or W.colors.button,100)
    background:set_intercepts_operations(false)
    local padding=h<30 and 2 or 3
    local label=W.label(ui,8,padding,w-16,h-padding*2,text,h<30 and 13 or 16,primary and '#e3fff6' or W.colors.text)
    ui:add_local_event('左键-点击',function(player) callback(player) end)
    return {ui=ui,label=label,background=background,set=function(self,value,enabled)
        self.label:set_text(value);self.ui:set_button_enable(enabled~=false)
        image_color(self.background,enabled==false and W.colors.deep or primary and '#25645f' or W.colors.button,100)
        self.label:set_text_color_hex(enabled==false and W.colors.muted or primary and '#e3fff6' or W.colors.text,100)
    end}
end
function W.image(parent,x,y,w,h,texture)
    local ui=place(parent:create_child('图片'),x,y,w,h)
    if texture then ui:set_image(texture) end
    ui:set_intercepts_operations(false)
    return ui
end
return W
