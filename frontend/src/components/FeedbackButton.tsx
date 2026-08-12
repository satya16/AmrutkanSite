import { useState } from 'react'
import { App as AntApp, Button, Form, Input, Modal } from 'antd'
import { MessageOutlined } from '@ant-design/icons'
import { submitFeedback } from '../api'

interface FeedbackFormValues {
  message: string
  contact?: string
  website?: string
}

export default function FeedbackButton() {
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form] = Form.useForm<FeedbackFormValues>()
  const { message: toast } = AntApp.useApp()

  const handleSubmit = async (values: FeedbackFormValues) => {
    setSubmitting(true)
    try {
      await submitFeedback({
        message: values.message.trim(),
        contact: (values.contact ?? '').trim(),
        website: values.website ?? '',
      })
      toast.success('अभिप्रायाबद्दल धन्यवाद!')
      form.resetFields()
      setOpen(false)
    } catch {
      toast.error('अभिप्राय पाठवता आला नाही, कृपया पुन्हा प्रयत्न करा')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <Button
        type="text"
        icon={<MessageOutlined style={{ color: '#fff', fontSize: 16 }} />}
        onClick={() => setOpen(true)}
        aria-label="अभिप्राय द्या"
        style={{ width: 22, height: 22, minWidth: 22, padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      />
      <Modal
        title="अभिप्राय"
        open={open}
        onCancel={() => setOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit} requiredMark={false}>
          <Form.Item
            name="message"
            label="तुमचा अभिप्राय"
            rules={[{ required: true, message: 'कृपया अभिप्राय लिहा' }, { max: 3000 }]}
          >
            <Input.TextArea rows={4} maxLength={3000} showCount placeholder="इथे लिहा..." />
          </Form.Item>
          <Form.Item name="contact" label="संपर्क (ऐच्छिक)" rules={[{ max: 200 }]}>
            <Input placeholder="ईमेल किंवा फोन नंबर" />
          </Form.Item>
          {/* Honeypot: hidden from real users (off-screen, unreachable by
              tab/screen reader), but a naive bot that fills every field will
              trip it — server silently drops submissions where it's set. */}
          <Form.Item name="website" style={{ position: 'absolute', left: -9999, top: -9999 }} aria-hidden>
            <Input tabIndex={-1} autoComplete="off" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Button type="primary" htmlType="submit" loading={submitting}>
              पाठवा
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
